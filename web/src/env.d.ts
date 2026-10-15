declare namespace App {
  interface Locals {
    /** The signed-in reader, from the session cookie (ADR 0003), or null. */
    reader: import("./lib/api/client").Me | null;
  }
}
