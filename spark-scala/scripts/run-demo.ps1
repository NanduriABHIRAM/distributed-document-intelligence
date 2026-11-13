param(
    [string]$OutputPrefix = "",
    [int]$Partitions = 2
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputPrefix) { $OutputPrefix = Join-Path $projectRoot ("demo-output/run-" + (Get-Date -Format "yyyyMMdd-HHmmss")) }
$jar = Join-Path $projectRoot "target/scala-2.12/distributed-document-intelligence-etl_2.12-0.1.0.jar"
if (-not (Test-Path -LiteralPath $jar)) { throw "Build the Scala JAR with sbt test package first." }
if (-not (Get-Command spark-submit -ErrorAction SilentlyContinue)) { throw "Install Spark 3.5.1 and add its bin directory to PATH." }
& spark-submit --class DocumentETL --master 'local[2]' $jar (Join-Path $projectRoot 'demo/chunks.jsonl') $OutputPrefix $Partitions (Join-Path $projectRoot 'demo/evidence') --pagerank-iterations=5
if ($LASTEXITCODE -ne 0) { throw "Spark ETL failed. Review the Spark log above." }
& spark-submit --class tracerag.SearchIndex --master 'local[2]' $jar $OutputPrefix 'research laboratory' 5
if ($LASTEXITCODE -ne 0) { throw "Scala BM25 query failed." }
Write-Host "Completed. Output prefix: $OutputPrefix"
