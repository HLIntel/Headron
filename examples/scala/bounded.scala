/** Bounded retry: a flaky operation gets at most `tries` attempts, then the error escapes.
  * Run: scala bounded.scala
  */
object Bounded {
  def retry[A](tries: Int)(op: => A): A = {
    require(tries >= 1, "tries must be positive")
    var n = 0
    var last: Throwable = null
    while (n < tries) {
      n += 1
      try { return op }
      catch { case t: Throwable => last = t }
    }
    throw last
  }

  def main(args: Array[String]): Unit = {
    var attempts = 0
    val got = retry(5) {
      attempts += 1
      if (attempts < 3) throw new RuntimeException("flaky") else "ok"
    }
    assert(got == "ok" && attempts == 3, "must succeed on attempt 3 of 5")
    println("bounded: 1 assertion held — flaky op succeeded on attempt 3 of at most 5")
  }
}
