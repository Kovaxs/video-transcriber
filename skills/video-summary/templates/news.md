# News template

Use this template for announcements, releases, events, analysis, and commentary.

## Research targets

Do two research passes:

- For *What's new*: what is announced or released, and does outside coverage confirm or contradict the video's claims? Find the primary source (repo, paper, blog, press release).
- For *Behind the news*: background, reactions, criticism, earlier events, who said what, and the competitive or regulatory context.

## Structure

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

## Template rules

- **Title:** a clear headline for the topic, not the video's clickbait title. For example, `# DeepSeek Deep Infer - How Open-Sourcing an Inference Engine Triples GPU Output`.
- **Section 1:** include it only if the user asked concrete questions that sections 2–5 do not already answer. If you skip it, keep the other headings numbered 2 to 6.
- **Tone:** plain, factual, neutral in every section except *We're thinking*.
- **Length:** about 500–900 words total. Shorter videos get shorter summaries.
