/** Test the Pi setup dialog without downloads or external commands. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import videoSetup from "../extensions/video-setup.ts";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const phonon = {
  model_id: "phonon-2",
  display_name: "Phonon-2",
  backend: "fermion",
  languages: [{ code: "en", name: "English" }],
  download_size_mb: 158,
  recommended: true,
};
const success = { stdout: "", stderr: "", code: 0, killed: false, truncated: false };

function harness({ models = [phonon], select = (options) => options[0], execute } = {}) {
  const commands = new Map();
  const calls = [];
  const notices = [];
  const dialogs = [];
  const statuses = [];
  const api = {
    registerCommand(name, command) {
      commands.set(name, command);
    },
    async exec(command, args, options) {
      calls.push({ command, args, options });
      const override = await execute?.(command, args);
      if (override) return override;
      if (args[0] === "models") return { ...success, stdout: JSON.stringify(models) };
      if (args.join(" ") === "tool dir --bin") return { ...success, stdout: "/tmp/video tool bin\n" };
      return success;
    },
  };
  videoSetup(api);
  const ctx = {
    hasUI: true,
    ui: {
      async select(title, options) {
        dialogs.push({ title, options });
        return select(options);
      },
      notify(message, level) { notices.push({ message, level }); },
      setStatus(key, value) { statuses.push({ key, value }); },
    },
  };
  const handler = commands.get("video-setup").handler;
  return { calls, notices, dialogs, statuses, ctx, run: (args = "") => handler(args, ctx) };
}

test("the Pi manifest exposes the setup extension and summary skill", async () => {
  const manifest = JSON.parse(await readFile(join(packageRoot, "package.json"), "utf8"));
  assert.deepEqual(manifest.pi.extensions, ["./extensions/video-setup.ts"]);
  assert.deepEqual(manifest.pi.skills, ["./skills"]);
});

test("setup installs from its own package and uses a Pi dialog", async () => {
  const h = harness();
  await h.run();
  assert.deepEqual(h.calls.map(({ command, args }) => [command, args]), [
    ["uv", ["--version"]],
    ["uv", ["tool", "install", "--python", "3.12", "--force", packageRoot]],
    ["uv", ["tool", "dir", "--bin"]],
    ["/tmp/video tool bin/video-transcriber", ["models"]],
    ["/tmp/video tool bin/video-transcriber", ["setup", "--model", "phonon-2"]],
  ]);
  assert.ok(h.calls.every(({ options }) => options.cwd === packageRoot));
  assert.equal(h.dialogs.length, 1);
  assert.match(h.dialogs[0].title, /all supported languages/);
  assert.match(h.dialogs[0].options[0], /Phonon-2 \(recommended\).*English.*158 MB/);
  assert.match(h.notices.at(-1).message, /Setup is complete/);
  assert.equal(h.statuses.at(-1).value, undefined);
});

test("the model selection comes from the CLI catalog", async () => {
  const second = {
    ...phonon,
    model_id: "test-model",
    display_name: "Test model",
    languages: [{ code: "en", name: "English" }, { code: "de", name: "German" }],
    recommended: false,
  };
  const h = harness({ models: [second, phonon], select: (options) => options[1] });
  await h.run();
  assert.match(h.dialogs[0].options[0], /Phonon-2 \(recommended\)/);
  assert.match(h.dialogs[0].options[1], /English, German/);
  assert.ok(!h.dialogs[0].title.includes("Phonon-2"));
  assert.deepEqual(h.calls.at(-1).args, ["setup", "--model", "test-model"]);
});

test("Escape cancels before the model download", async () => {
  const h = harness({ select: () => undefined });
  await h.run();
  assert.ok(h.calls.every(({ args }) => args[0] !== "setup"));
  assert.match(h.notices.at(-1).message, /Setup cancelled/);
  assert.equal(h.statuses.at(-1).value, undefined);
});

test("missing uv stops setup with an installation link", async () => {
  const h = harness({ execute: () => ({ ...success, code: 1, stderr: "spawn uv ENOENT" }) });
  await h.run();
  assert.equal(h.calls.length, 1);
  assert.equal(h.dialogs.length, 0);
  assert.match(h.notices.at(-1).message, /https:\/\/docs.astral.sh\/uv\//);
  assert.equal(h.notices.at(-1).level, "error");
});

for (const stage of ["install", "models", "setup"]) {
  test(`a failed ${stage} command reports the error without success`, async () => {
    const h = harness({
      execute: (_command, args) => args.includes(stage)
        ? { ...success, code: 1, stderr: "test failure" }
        : undefined,
    });
    await h.run();
    assert.match(h.notices.at(-1).message, /test failure/);
    assert.equal(h.notices.at(-1).level, "error");
    assert.ok(h.notices.every(({ message }) => !message.includes("Setup is complete")));
    assert.equal(h.statuses.at(-1).value, undefined);
  });
}

for (const models of [[], null]) {
  test(`an invalid catalog ${JSON.stringify(models)} stops setup`, async () => {
    const h = harness({ models });
    await h.run();
    assert.equal(h.dialogs.length, 0);
    assert.equal(h.notices.at(-1).level, "error");
    assert.ok(h.calls.every(({ args }) => args[0] !== "setup"));
  });
}

test("invalid JSON reports an error", async () => {
  const h = harness({
    execute: (_command, args) => args[0] === "models" ? { ...success, stdout: "not JSON" } : undefined,
  });
  await h.run();
  assert.equal(h.dialogs.length, 0);
  assert.equal(h.notices.at(-1).level, "error");
});

test("an unknown dialog result cannot select an arbitrary model", async () => {
  const h = harness({ select: () => "arbitrary-model" });
  await h.run();
  assert.ok(h.calls.every(({ args }) => args[0] !== "setup"));
  assert.equal(h.notices.at(-1).level, "error");
});

test("non-interactive mode cannot start an installation", async () => {
  const h = harness();
  h.ctx.hasUI = false;
  await assert.rejects(h.run(), /needs Pi dialogs/);
  assert.equal(h.calls.length, 0);
});

test("arguments cannot bypass the model dialog", async () => {
  const h = harness();
  await h.run("--model arbitrary-model");
  assert.equal(h.calls.length, 0);
  assert.equal(h.notices.at(-1).level, "error");
});

test("overlapping setup calls do not start another installation", async () => {
  let finish;
  const pending = new Promise((resolve) => { finish = resolve; });
  const h = harness({ execute: (_command, args) => args[0] === "--version" ? pending : undefined });
  const first = h.run();
  await h.run();
  assert.equal(h.calls.length, 1);
  assert.match(h.notices.at(-1).message, /already active/);
  finish(success);
  await first;
});

test("a later setup can run after cancellation", async () => {
  const h = harness({ select: () => undefined });
  await h.run();
  await h.run();
  assert.equal(h.dialogs.length, 2);
});

test("terminated commands cannot report success", async () => {
  const h = harness({
    execute: (_command, args) => args[0] === "setup" ? { ...success, killed: true } : undefined,
  });
  await h.run();
  assert.equal(h.notices.at(-1).level, "error");
});
