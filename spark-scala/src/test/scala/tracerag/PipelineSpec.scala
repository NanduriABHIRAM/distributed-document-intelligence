package tracerag

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types.StructType
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

class PipelineSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var session: SparkSession = _
  override def beforeAll(): Unit = {
    session = SparkSession.builder.master("local[2]").appName("TraceRAG Scala tests")
      .config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "2")
      .config("spark.driver.host", "127.0.0.1").getOrCreate()
    session.sparkContext.setLogLevel("ERROR")
  }
  override def afterAll(): Unit = if (session != null) session.stop()

  private def json(schema: StructType, rows: String*): DataFrame = {
    val spark = session
    import spark.implicits._
    spark.read.schema(schema).json(rows.toDS())
  }
  private val chunk = """{"chunk_id":"c1","document_id":"d1","source_path":"paper.txt","text":"alpha beta","start_offset":0,"end_offset":10,"file_type":"txt"}"""
  private val source = """"source":{"chunk_id":"c1","document_id":"d1","source_path":"paper.txt","source_text":"alpha beta"}"""
  private def entities: DataFrame = json(Schemas.entities,
    s"""{"entity_id":"e1","text":"alpha","normalized_text":"alpha","entity_type":"PERSON","validation_status":"VALID",$source}""",
    s"""{"entity_id":"e2","text":"beta","normalized_text":"beta","entity_type":"PERSON","validation_status":"VALID",$source}""")

  test("configuration preserves positional API arguments and validates flags") {
    assert(JobConfig.parse(Array("in", "out", "4", "evidence")).strict)
    assert(!JobConfig.parse(Array("in", "out", "2", "--quarantine")).strict)
    intercept[IllegalArgumentException](JobConfig.parse(Array("in", "out", "0")))
    intercept[IllegalArgumentException](JobConfig.parse(Array("in", "out", "2", "--unknown")))
  }

  test("chunk validation keeps original text and identifies offset errors") {
    val rows = ChunkQuality.annotate(json(Schemas.chunks, chunk, chunk.replace("c1", "c2").replace("10,", "9,")))
    assert(rows.filter(col("is_valid")).count() == 1)
    assert(rows.filter(!col("is_valid")).head().getAs[Seq[String]]("quality_errors").contains("offset_length_mismatch"))
    assert(rows.filter(col("is_valid")).head().getAs[String]("text") == "alpha beta")
  }

  test("duplicate IDs quarantine every conflicting record") {
    val rows = ChunkQuality.annotate(json(Schemas.chunks, chunk, chunk))
    assert(rows.filter(col("is_valid")).count() == 0)
    assert(ChunkQuality.report(rows).head().getAs[Long]("count") == 2)
  }

  test("malformed JSON and missing fields are quarantined") {
    val rows = ChunkQuality.annotate(json(Schemas.chunks, "{broken", "{}"))
    assert(rows.filter(col("is_valid")).count() == 0)
    assert(rows.select(explode(col("quality_errors"))).collect().exists(_.getString(0) == "malformed_json"))
  }

  test("content duplicates retain both source identities and document counts") {
    val rows = ChunkQuality.annotate(json(Schemas.chunks, chunk, chunk.replace("c1", "c2").replace("d1", "d2")))
    val duplicate = ChunkQuality.duplicates(rows).head()
    assert(duplicate.getAs[Long]("occurrences") == 2)
    assert(duplicate.getAs[Long]("document_count") == 2)
    assert(CorpusAnalytics.documents(rows).count() == 2)
  }

  test("BM25 scores match the formula and ignore repeated query terms") {
    val spark = session
    import spark.implicits._
    val corpus = Seq(("a", "alpha alpha beta"), ("b", "beta gamma")).toDF("chunk_id", "text")
    val index = LexicalIndex.build(corpus)
    val result = LexicalIndex.search(index, "alpha alpha").head()
    val expected = math.log(2.0) * 2 * 2.2 / (2 + 1.2 * (0.25 + 0.75 * 3 / 2.5))
    assert(result.getAs[String]("chunk_id") == "a")
    assert(math.abs(result.getAs[Double]("bm25_score") - expected) < 1e-9)
    assert(LexicalIndex.search(index, "unseen").count() == 0)
  }

  test("BM25 supports Unicode and an empty corpus") {
    val spark = session
    import spark.implicits._
    val corpus = Seq(("a", "தமிழ் café")).toDF("chunk_id", "text")
    assert(LexicalIndex.search(LexicalIndex.build(corpus), "café").count() == 1)
    assert(LexicalIndex.search(LexicalIndex.build(corpus.limit(0)), "alpha").count() == 0)
  }

  test("evidence marked VALID still requires a matching source") {
    val corpus = json(Schemas.chunks, chunk)
    val input = entities.withColumn("source", struct(lit("wrong").as("document_id"), lit("c1").as("chunk_id"), lit("paper.txt").as("source_path"), lit("alpha beta").as("source_text")))
    val rejected = EvidenceAnalytics.validate(input, corpus, "entity_id", Seq("text", "entity_type"))
    assert(rejected.accepted.count() == 0)
    assert(rejected.rejected.count() == 2)
    assert(EvidenceAnalytics.validate(entities, corpus, "entity_id", Seq("text", "entity_type")).accepted.count() == 2)
  }

  test("dangling relationship endpoints never enter graph outputs") {
    val records = json(Schemas.relationships,
      s"""{"relationship_id":"r1","source_entity_id":"e1","target_entity_id":"e2","relationship_type":"KNOWS",$source}""",
      s"""{"relationship_id":"r2","source_entity_id":"e1","target_entity_id":"missing","relationship_type":"KNOWS",$source}""")
    val split = EvidenceAnalytics.relationships(records, entities)
    assert(split.accepted.count() == 1)
    assert(split.rejected.count() == 1)
  }

  test("PageRank preserves probability mass including isolated nodes") {
    val spark = session
    import spark.implicits._
    val nodes = Seq(("a", "A", "PERSON"), ("b", "B", "PERSON"), ("c", "C", "PERSON")).toDF("id", "label", "entity_type")
    val edges = Seq(("a", "b")).toDF("source", "target")
    val ranks = GraphAnalytics.pageRank(nodes, edges, iterations = 3)
    try {
      assert(math.abs(ranks.agg(sum("pagerank")).head().getDouble(0) - 1.0) < 1e-9)
      assert(ranks.orderBy(desc("pagerank")).head().getAs[String]("id") == "b")
      assert(GraphAnalytics.degrees(nodes, edges).filter(col("id") === "c").head().getAs[Long]("degree") == 0)
    } finally ranks.unpersist()
  }

  test("timeline excludes inferred dates and claim review is qualified") {
    val events = json(Schemas.events,
      """{"event_id":"a","event_date":"2024","date_is_explicit":true}""",
      """{"event_id":"b","event_date":"2025","date_is_explicit":false}""")
    assert(EvidenceAnalytics.timeline(events).count() == 1)
    val claims = json(Schemas.claims,
      """{"claim_id":"a","subject":"Acme","predicate":"revenue","object":"100","negated":false}""",
      """{"claim_id":"b","subject":"Acme","predicate":"revenue","object":"200","negated":false}""")
    assert(EvidenceAnalytics.claimReview(claims).head().getAs[String]("review_status") == "CANDIDATE_REQUIRES_REVIEW")
  }
}
