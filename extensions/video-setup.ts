/** Provide the Pi setup command and its speech model dialog. */
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

interface CatalogModel {
  model_id: string;
  display_name: string;
  backend: string;
  languages: { code: string; name: string }[];
  download_size_mb: number;
  recommended: boolean;
}

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));

export default function videoSetup(pi: ExtensionAPI): void {
  let running = false;

  pi.registerCommand("video-setup", {
    description: "Install video-transcriber and select a local speech model",
    handler: async (args, ctx) => {
      if (!ctx.hasUI) {
        throw new Error("/video-setup needs Pi dialogs. Use video-transcriber setup in a terminal.");
      }
      if (args.trim()) {
        ctx.ui.notify("Use /video-setup without arguments. Select a model in the dialog.", "error");
        return;
      }
      if (running) {
        ctx.ui.notify("Video setup is already active.", "warning");
        return;
      }
      running = true;

      const run = async (command: string, commandArgs: string[], stage: string): Promise<string> => {
        ctx.ui.setStatus("video-setup", stage);
        const result = await pi.exec(command, commandArgs, { cwd: packageRoot });
        if (result.code !== 0 || result.killed || result.truncated) {
          const output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
          throw new Error(`${stage} failed.\n${output.slice(-4000) || "The command returned no output."}`);
        }
        return result.stdout.trim();
      };

      try {
        const uv = await pi.exec("uv", ["--version"], { cwd: packageRoot });
        if (uv.code !== 0) {
          ctx.ui.notify("uv is missing. Install it from https://docs.astral.sh/uv/ and run /video-setup again.", "error");
          return;
        }

        ctx.ui.notify("The setup will install the CLI, then ask for a speech model.", "info");
        await run("uv", ["tool", "install", "--python", "3.12", "--force", packageRoot], "Install video-transcriber");
        const binDir = await run("uv", ["tool", "dir", "--bin"], "Find the CLI");
        const cli = join(binDir, "video-transcriber");
        const catalog = await run(cli, ["models"], "Read the model catalog");
        const models: CatalogModel[] = JSON.parse(catalog);
        if (!Array.isArray(models) || models.length === 0) {
          throw new Error("The supported model catalog is empty or invalid.");
        }
        models.sort((a, b) => Number(b.recommended) - Number(a.recommended));
        const options = models.map((model) => {
          const languages = model.languages.map((language) => language.name).join(", ");
          const recommendation = model.recommended ? " (recommended)" : "";
          return `${model.display_name}${recommendation} — Languages: ${languages} — ${model.download_size_mb} MB`;
        });
        ctx.ui.setStatus("video-setup", undefined);
        const choice = await ctx.ui.select("Select a speech model. Each option lists all supported languages.", options);
        if (choice === undefined) {
          ctx.ui.notify("Setup cancelled. The CLI is installed. No model download started.", "info");
          return;
        }
        const model = models[options.indexOf(choice)];
        if (!model) {
          throw new Error("Select a model from the supported catalog.");
        }

        ctx.ui.notify(`The setup will check dependencies and download ${model.display_name}. A cached model needs no download.`, "info");
        await run(cli, ["setup", "--model", model.model_id], `Set up ${model.display_name}`);
        ctx.ui.notify(`Setup is complete. Selected model: ${model.display_name}. Use /skill:video-summary <URL-or-local-path>.`, "info");
      } catch (error) {
        ctx.ui.notify(error instanceof Error ? error.message : String(error), "error");
      } finally {
        running = false;
        ctx.ui.setStatus("video-setup", undefined);
      }
    },
  });
}
