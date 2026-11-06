---
name: youtube-captions
description: Fetch the captions of a YouTube video and write a structured, researched summary of it (answers to the user's questions, what's new, how it works, behind the news, why it matters, and an opinion). Use whenever the user shares a youtube.com / youtu.be link and asks what it says, for a summary, a transcript or captions, or asks a question about its content. Works without login or API key, and is the fallback when fetch_content fails on YouTube.
---

# YouTube captions → researched summary

Default output is the **summary** (see "Summary template"). Give only the raw transcript if the user asks for just that.

## Workflow
1. **Get the video ID.** The CLI takes the 11-character ID, not a URL. Extract it from `v=`, `youtu.be/`, `shorts/` or `embed/`.
2. **Get metadata** (title, channel, upload date, duration):
   `yt-dlp --skip-download --print "%(title)s|%(uploader)s|%(duration)s|%(upload_date)s" <url>`
3. **Get captions** (see "Fetching captions") and read the whole file in chunks. Don't summarize from the first chunk only.
4. **List the user's concrete questions** from their message. If there are none, skip section 1 of the template.
5. **Research the topic on the web before writing** (`web_search` with 2–4 varied queries, then `fetch_content` on the best sources). Do this twice:
   - For *What's new*: what is announced or released, and does outside coverage confirm or contradict the video's claims? Find the primary source (repo, paper, blog, press release).
   - For *Behind the news*: background, reactions, criticism, earlier events, who said what, and the competitive or regulatory context.
6. **Write the summary** in the template below. Mark each fact by its source: "the video says…" when it comes only from the captions, and name the source for web-sourced facts. If the web contradicts the video, say so.

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
Uses the `youtube_transcript_api` CLI (unofficial client by Jonas Depoix, https://github.com/jdepoix/youtube-transcript-api, MIT).

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
- `TranscriptsDisabled` / `NoTranscriptFound`: the video has no captions. Tell the user. A fallback is downloading the audio with yt-dlp and transcribing it, but only if the user wants that.
- `RequestBlocked` / `IpBlocked`: YouTube is rate-limiting this IP. Wait, or use `--https-proxy`.
- `yt-dlp --print` metadata can also fail on 429. Then take the title from the web search or the page.
