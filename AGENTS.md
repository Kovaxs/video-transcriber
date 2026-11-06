# Development Rules

## Project Purpose

video-transcriber is a local tool. It changes a video URL or a local media file into a transcript.

### Problem

A user gives a video URL. The user wants a transcript or a researched summary of the video. Some videos have captions on the provider. Other videos have no captions, or the provider does not show the captions.

The user can also give a local audio file or a local video file. A local file has no provider captions.

Example: the URL `https://hackertube.org/watch/S4gU2Tsv6hY` is a HackerTube page. HackerTube is a frontend for YouTube videos. The HackerTube page and its API give only metadata. They do not give captions.

### Solution

The tool has two paths:

1. **Yes path (captions exist).** The tool gets the captions from the provider. This path works now through `youtube_transcript_api`. Do not change it unless the user asks.
2. **No path (captions do not exist).** The tool downloads the audio of the video. Then the tool transcribes the audio locally with a speech recognition model. For a local audio file or a local video file, the tool does not download. It converts the file to audio with ffmpeg.

The provider is only an input. The tool uses the provider only to get metadata and audio. The speech recognition runs on the local machine. The tool does not send audio or text to an external transcription service.

### Pipeline for the No path

```text
video URL (HackerTube, YouTube, other providers)      local audio or video file
        |                                                   |
        v                                                   v
get metadata and audio (yt-dlp, 16 kHz mono WAV)     convert to 16 kHz mono WAV (ffmpeg)
        |                                                   |
        +---------------------------------------------------+
        |
        v
transcribe locally (Phonon-2)
        |
        v
TXT, SRT, VTT, JSON with word timestamps
        |
        v
skill: read the full transcript, do web research, write the summary
```

### Current scope (step 1)

- Use English transcription only. Do this also when the user asks for a different language. The summary skill can write the summary in the language of the user.
- Use Phonon-2 as the only speech recognition model. Phonon-2 is a 164 MB, English-only, 2.1-bit quantized version of NVIDIA Parakeet TDT 0.6B v3. It runs on Apple silicon through MLX. Model page: https://www.fermionresearch.com/models/phonon-2/
- Use yt-dlp to download audio. Start with HackerTube URLs. Extract the YouTube video ID from the HackerTube URL. Other providers that yt-dlp supports must work with no special code where possible.
- Accept a local audio file or a local video file as input. Use ffmpeg to extract the audio. Use the file name as the title in the metadata.
- Test the full chain with the HackerTube URL above. That video ("The Iroquois Confederacy", Historia Civilis) has manually created English captions on YouTube. Use these captions as the reference to measure the word error rate (WER) of the No path.

### Out of scope (later steps)

- Language detection.
- Whisper as the model for languages that are not English.
- Translation.
- Automatic choice between the Yes path and the No path. For now, the skill makes this choice.
- Automatic installation of the model and dependencies. A later setup command will do this work.

### Repository and skill

The repository and the skill have different jobs. Keep them separate.

- **Repository:** deterministic work. URL parsing, audio download, model calls, output formats, caches, temporary files, errors, tests. The Python code must not use an LLM. It must not know about pi.
- **Pi package:** `package.json` makes the repository a pi package. It exposes `skills/` to pi. Install command: `pi install https://github.com/Kovaxs/video-transcriber`. This command installs the Pi skill. Install the Python CLI separately with `uv tool install`. Do not put a copy of the skill in `~/.agents/skills/`.
- **Skill** (`skills/youtube-captions/SKILL.md`): agent workflow. Choose the path, call the CLI of this repository for the No path, read the full transcript, do web research, write the summary with the template and the ASD-STE100 rules.

Target CLI:

```bash
video-transcriber transcribe <URL> --format srt
video-transcriber transcribe ./talk.mp4 --format srt
```

### Layout

```text
video-transcriber/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── package.json     pi package manifest (skills only)
├── skills/youtube-captions/SKILL.md
├── src/video_transcriber/
│   ├── cli.py       command-line entry point
│   ├── media.py     URL parsing, metadata, audio download, local file conversion
│   ├── phonon.py    Phonon-2 transcription and data types
│   ├── formats.py   TXT, SRT, VTT, JSON output
│   └── errors.py    Shared command-line errors
└── tests/
```

### Development machine

- Apple M1 Max, 32 GB, macOS. The Phonon-2 speed numbers on the model page come from an M5 MacBook Air. Measure the speed again on this machine. Do not copy the vendor numbers as results.
- Available tools: `uv`, `yt-dlp`, `ffmpeg`, `youtube_transcript_api`, `jj`.

## Conversational Style

- Keep answers short and concise
- No emojis in commits, issues, PR comments, or code
- No fluff or cheerful filler text
- Technical prose only, be direct
- Use concise, clear, simple language. Define unavoidable jargon before using it.
- Explain non-trivial designs and problems as: problem, concrete example or short trace, then solution. State why the solution is necessary and distinguish it from optional complexity.
- Prefer concrete behavior and small illustrations over abstract summaries, dense terminology, or unexplained lists of changes.
- When the user asks a question, answer it first before making edits or running implementation commands.
- When responding to user feedback or an analysis, explicitly say whether you agree or disagree before saying what you changed.

## Response Style (ASD-STE100)

Write all responses to the user, and all documentation, in ASD-STE100 Simplified Technical English. Code, commands, and identifiers stay as they are.

- Use short sentences. Maximum 25 words in descriptive text. Maximum 20 words in instructions.
- Write one idea in each sentence. Keep paragraphs to 6 sentences or fewer.
- Use the active voice and the simple tenses (present, past, future). Avoid the passive voice, the perfect tenses, and the "-ing" form as a verb.
- Use one word for one meaning. Use the same word for the same thing every time. Do not use synonyms to vary the text.
- Use simple, common words. Prefer "use" to "utilize", "start" to "initiate", "show" to "demonstrate", "about" to "approximately".
- Do not use phrasal verbs with unclear meaning, idioms, slang, or figures of speech.
- Always use articles ("a", "the"). Put the verb near the subject. Use "the" or "this" with a noun, not alone.
- Keep technical terms, product names, model names, and numbers exact. Explain a technical term the first time you use it.
- Use "must" for a required action and "can" for a possible action. Avoid "should", "may", and "might" when a firm statement is correct.
- Write numbers as digits. Write each date in full (for example, 6 November 2026).
- Write in the language of the user. If it is not English, use the same simple, short-sentence style in that language.

## Code Quality

- Read files in full before wide-ranging changes, before editing files you have not fully inspected, and when asked to investigate or audit. Do not rely on search snippets for broad changes.
- Python 3.12. Use type hints on all public functions. No `Any` unless absolutely necessary.
- Top-level imports only. No imports inside functions, except for a heavy optional dependency (for example, MLX) with a comment that gives the reason.
- Inline single-line helpers that have only one call site.
- Read the installed package source for external API types and signatures; don't guess.
- One concept per module. The first line of each module is a docstring that says what the module is for.
- Use `subprocess.run` with an argument list for external tools (yt-dlp, ffmpeg). Never use `shell=True`.
- Never remove or downgrade code to fix type errors from outdated deps; upgrade the dep instead.
- Always ask before removing functionality or code that appears intentional.
- Do not preserve backward compatibility unless the user asks for it.

## Commands

- Manage the environment and dependencies with `uv` only (`uv add`, `uv sync`, `uv run`).
- After code changes (not docs): `uv run ruff check`, `uv run ruff format --check`, and `uv run pyright`. Fix all errors and warnings.
- Run the tests with `uv run pytest`. Tests must not download models or audio from the network. Put tests that use the network or the model behind the `integration` marker, and run them only when the user asks.
- If you create or modify a test file, run it and iterate on test or implementation until it passes.
- For ad-hoc scripts, `write` them to a temp file (e.g. `/tmp`), run, edit if needed, remove when done. Don't embed multi-line scripts in `bash` commands.
- Put downloaded audio and model files in a cache directory, not in the repository.
- Never commit unless the user asks.

## Dependency and Install Security

- Treat dependency and `uv.lock` changes as reviewed code. Pin direct dependencies to exact versions.
- Read the release notes before an update of yt-dlp or of the Phonon-2 packages. Check if the changes can affect the behavior of the tool.

## Version Control (jj)

This repository uses jj (Jujutsu) with a colocated Git repository. Use `jj` commands, not `git` commands, for changes to history.

Multiple pi sessions can run in this directory at the same time. jj records all files in the working copy automatically. Follow these rules:

- Only commit files YOU changed in THIS session. If other files changed, use `jj split <paths>` to keep only your files in your change.
- Before committing, run `jj status` and `jj diff --summary` and verify the changed files.
- Commit with `jj commit -m "<message>"` or set the message with `jj describe -m "<message>"`.
- Message format: `{feat,fix,docs,test,chore}[(scope)]: <commit message>`. Scopes: `cli`, `media`, `phonon`, `formats`, `skill`. Message is informative and concise.
- Never run `jj abandon` on changes that you did not create, `jj restore` on files that you did not change, or `git push --force`.
- If a conflict occurs in a file you did not modify, stop and ask the user.

## User Override

If the user's instructions conflict with any rule in this document, ask for explicit confirmation before overriding. Only then execute their instructions.
