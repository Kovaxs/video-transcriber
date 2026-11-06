---
name: video-summary
description: Transcribe a YouTube video, a HackerTube video, another supported URL, or a local media file. Write a structured, researched summary with answers, new information, mechanisms, context, implications, and an opinion. Use provider captions when they exist. Use the local video-transcriber CLI and Phonon-2 when captions do not exist. Requires an explicit slash command.
disable-model-invocation: true
---

# Video transcript → researched summary

Default output is the **summary** (see "Summary template"). Give only the raw transcript if the user asks for just that.

## Setup
If the argument is exactly `setup`, do these steps and stop:
1. Check for `uv`. If it is missing, give the user the installation page: https://docs.astral.sh/uv/. Stop.
2. Check for `video-transcriber`. If it is missing, run:
   `uv tool install --python 3.12 git+https://github.com/Kovaxs/video-transcriber.git`
3. Run `video-transcriber setup`. Let the user answer the model prompt. Phonon-2 is the recommended model. It transcribes English only.
4. Report the setup result. Do not transcribe a video and do not do web research.

## Workflow
1. **Choose the transcript path.** For a YouTube URL, use the Yes path in "Fetching captions". For a HackerTube URL, another URL, or a local media file, use the No path below. If YouTube has no captions, use the No path.
2. **Use the Yes path when captions exist.** Extract the 11-character video ID from `v=`, `youtu.be/`, `shorts/`, or `embed/`. Get the captions and read the whole file in chunks. Get the title, channel, upload date, and duration with `yt-dlp`.
3. **Use the No path when captions do not exist.** Create a temporary JSON path with `mktemp /tmp/video-transcriber.XXXXXX.json`. Then run:
   `video-transcriber transcribe <URL-or-local-path> --format json --output <temporary-path>`
   Read the whole JSON file in chunks. The `text` field contains the transcript. The `source` field contains the metadata. Do not summarize only the first chunk.
4. **List the user's concrete questions** from their message. If there are none, skip section 1 of the template.
5. **Research the topic on the web before writing** (`web_search` with 2–4 varied queries, then `fetch_content` on the best sources). Do this twice:
   - For *What's new*: what is announced or released, and does outside coverage confirm or contradict the video's claims? Find the primary source (repo, paper, blog, press release).
   - For *Behind the news*: background, reactions, criticism, earlier events, who said what, and the competitive or regulatory context.
6. **Write the summary** in the template below. Mark each fact by its source: "the video says…" when it comes only from the transcript, and name the source for web-sourced facts. If the web contradicts the video, say so.

## Summary template
Force this exact markdown structure: same heading levels, same numbering, same order. Write prose paragraphs under each heading, not bullet lists. The only exceptions are section 1, which is a bullet list, and short lists inside section 3 that enumerate parallel items.

```markdown
# <Topic title>

## 1. User questions
- **<Question 1 as the user asked it>** <Direct answer first, then the support from the video and the web.>
- **<Question 2>** <Answer.>

## 2. What's new
<What was announced or released, who did it, when, and the headline numbers. Before writing, search the topic and compare with the video's claims. Flag anything the video says that sources don't confirm, or that sources contradict.>

## 3. How it works
<Mechanism and technical or product details in several paragraphs. Include figures, limits, and caveats that the video gives. Explain jargon on first use.>

## 4. Behind the news
<Needs web research. Context before this event, reactions from critics and supporters (named, with sources), competing approaches, business or regulatory background, anything the video omits.>

## 5. Why it matters
<Implications for the industry, users, or competitors. Say who is affected and what to watch next.>

## 6. We're thinking
<Your own opinion, in first person plural, in a short paragraph. Take a position and justify it. Say what you're unsure about. This is the one section where it is fine to go beyond the sources.>
```

Template rules:
- **Title:** a clear headline for the topic, not the video's clickbait title. Never use a colon (`:`) in it. Use a hyphen (`-`) if a separator is needed, for example `# DeepSeek Deep Infer - How Open-Sourcing an Inference Engine Triples GPU Output`.
- **Section 1:** include it only if the user asked concrete questions that the sections below don't already answer. Skip the whole section, heading included, if the user only asked for a summary, or if their questions are fully covered by sections 2–5. When skipped, keep the other headings numbered 2 to 6 so the structure doesn't change.
- Keep the headings word for word, including numbers and the `##` level. Do not add, rename, merge, or reorder sections, and do not add a subtitle line under the title.

Language style: write all of the summary in **ASD-STE100 Simplified Technical English**. Apply it to every section, including section 6.
- Use short sentences. Maximum 25 words in descriptive text. Maximum 20 words in instructions.
- Write one idea in each sentence. Keep paragraphs to 6 sentences or fewer.
- Use the active voice and the simple tenses (present, past, future). Avoid the passive voice, the perfect tenses, and the "-ing" form as a verb (gerund).
- Use one word for one meaning, and use the same word for the same thing every time. Do not use synonyms to vary the text.
- Use simple, common words. Prefer "use" to "utilize", "start" to "initiate", "show" to "demonstrate", "about" to "approximately".
- Do not use phrasal verbs with unclear meaning, idioms, slang, or figures of speech.
- Always use articles ("a", "the") and put the verb near the subject. Use "the" or "this" with a noun, not alone.
- Keep technical terms, product names, model names, and numbers exact. Explain a technical term the first time you use it.
- Use "must" for a required action and "can" for a possible action. Avoid "should", "may", and "might" when a firm statement is correct.
- Write numbers as digits. Write each date in full (for example, 3 November 2026).
- Write in the same language as the user's message. If it is not English, keep the same simple, short-sentence style in that language.

Style rules:
- Plain, factual, neutral tone in every section except *We're thinking*.
- Keep numbers exact. Use the video's figures, and say if they are vendor-reported or estimates by the creator.
- Dates: use absolute dates, and state the video's upload date.
- Length: about 500–900 words total. Shorter videos get shorter summaries.
- End with a one-line source list: the video (title, channel) and the main web sources.
- Captions are auto-generated. Names, model names, and numbers may be transcribed wrongly, so cross-check them with the web before repeating them.

## Fetching captions
Get the metadata with:

```bash
yt-dlp --skip-download --print "%(title)s|%(uploader)s|%(duration)s|%(upload_date)s" <url>
```

Use the `youtube_transcript_api` CLI (unofficial client by Jonas Depoix, https://github.com/jdepoix/youtube-transcript-api, MIT).

Setup once: `uv tool install youtube-transcript-api` (remove with `uv tool uninstall youtube-transcript-api`).

```bash
# plain text to a file (default)
youtube_transcript_api <VIDEO_ID> --languages en --format text > /tmp/cap.txt

# list available languages
youtube_transcript_api <VIDEO_ID> --list-transcripts

# timestamps: json has start times. Others: pretty, webvtt, srt
youtube_transcript_api <VIDEO_ID> --languages en --format json > /tmp/cap.json

# translate
youtube_transcript_api <VIDEO_ID> --languages en --translate es --format text
```
Options: `--languages en es` (priority order), `--exclude-generated`, `--exclude-manually-created`, `--http-proxy URL`, `--https-proxy URL`.

About 20k characters per 20 minutes of video. Read in chunks with `read` offset/limit.

## Why not the alternatives
1. `fetch_content` on a YouTube URL fails unless a Chromium Google login or `GEMINI_API_KEY` is available.
2. `yt-dlp --write-auto-subs` gets **HTTP 429** on the timedtext download, even with a JS runtime and EJS. Other player clients fail with "format not available".
3. `youtube_transcript_api` works.

## Troubleshooting
- `TranscriptsDisabled` / `NoTranscriptFound`: use the No path with the `video-transcriber` CLI.
- `video-transcriber: command not found`: tell the user to run `/skill:video-summary setup`.
- `RequestBlocked` / `IpBlocked`: YouTube is rate-limiting this IP. Wait, or use `--https-proxy`.
- `yt-dlp --print` metadata can also fail on 429. Then take the title from the web search or the page.
