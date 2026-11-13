package tracerag

case class JobConfig(input: String, output: String, partitions: Int,
  evidence: Option[String], strict: Boolean = true, pageRankIterations: Int = 10)

object JobConfig {
  val usage = "DocumentETL <chunks.jsonl> <output-prefix> <partitions> [evidence-directory] [--quarantine] [--pagerank-iterations=N]"
  def parse(args: Array[String]): JobConfig = {
    val positional = args.takeWhile(!_.startsWith("--"))
    val flags = args.drop(positional.length)
    require(positional.length == 3 || positional.length == 4, usage)
    require(flags.forall(flag => flag == "--quarantine" || flag.startsWith("--pagerank-iterations=")), usage)
    val partitions = positional(2).toInt
    val iterations = flags.find(_.startsWith("--pagerank-iterations=")).map(_.split("=", 2)(1).toInt).getOrElse(10)
    require(partitions > 0 && partitions <= 10000, "Partitions must be between 1 and 10000")
    require(iterations >= 1 && iterations <= 50, "PageRank iterations must be between 1 and 50")
    JobConfig(positional(0), positional(1).stripSuffix("/"), partitions, positional.lift(3), !flags.contains("--quarantine"), iterations)
  }
}
