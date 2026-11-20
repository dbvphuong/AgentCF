import test from "node:test";
import assert from "node:assert/strict";
import { serverOrigin } from "../../config.mjs";

test("permits loopback HTTP and network HTTPS origins", () => {
  assert.equal(serverOrigin(), "http://127.0.0.1:8000");
  assert.equal(serverOrigin("http://[::1]:8000/"), "http://[::1]:8000");
  assert.equal(serverOrigin("https://example.org/"), "https://example.org");
});

test("rejects credentials, nonlocal HTTP and non-origin proxy URLs", () => {
  for (const value of ["invalid", "http://example.org", "ftp://localhost", "http://user:secret@localhost", "http://localhost/path", "http://localhost?token=secret", "http://localhost/#fragment"]) {
    assert.throws(() => serverOrigin(value), /HTTP\(S\) origin/);
  }
});
