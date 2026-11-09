# Guide template

Use this template for tutorials, how-to videos, walkthroughs, courses, and setup demos. The reader must be able to do the task from the guide alone, without the video.

## Research targets

Do two research passes:

- For *Prerequisites* and *Steps*: find the official documentation for each tool, library, or product in the video. Check the current version, install command, flags, settings, and menu names. Note each step where the video is outdated or differs from the documentation.
- For *Problems and fixes*: find known errors, open issues, and forum answers for the task. Find better or simpler alternatives to the method in the video.

## Structure

Force this exact markdown structure: same heading levels, same numbering, same order. Write short prose under sections 2 and 8. Use lists where the template shows lists.

````markdown
# <Task title>

## 1. User questions
- **<Question 1 as the user asked it>** <Direct answer first, then the support from the video and the web.>
- **<Question 2>** <Answer.>

## 2. Goal
<What the reader can do at the end. The end result, who the guide is for, and the time that the task needs. State the versions and the platform that the video uses.>

## 3. Prerequisites
- <Tool, account, hardware, or knowledge, with the version. Add the install command or a link.>

## 4. Steps
1. **<Short action title>** <One action in the imperative. Give the reason when it is not clear.>
   ```bash
   <exact command, code, or setting>
   ```
   <Expected result. Add "The video uses X. The current documentation uses Y." when they differ.>
2. **<Next action>** <...>

## 5. Check the result
<How to make sure the task worked: a command, an output, a test, or a visible result. Give the expected output.>

## 6. Problems and fixes
- **<Symptom or error message>** <Cause and fix. Name the source.>

## 7. Reference
| Item | Value | Note |
|---|---|---|
| <command, setting, shortcut, or link> | <exact value> | <short note> |

## 8. We're thinking
<Your own opinion, in first person plural, in a short paragraph. Is this method good? Name a better alternative if one exists. Say what you're unsure about. This is the one section where it is fine to go beyond the sources.>
````

## Template rules

- **Title:** a task title that starts with a verb, not the video's clickbait title. For example, `# Run Llama 3 Locally on a Mac with Ollama`.
- **Section 1:** include it only if the user asked concrete questions that sections 2–7 do not already answer. If you skip it, keep the other headings numbered 2 to 8.
- **Steps:** keep the order of the video unless the order is wrong. Write one action in each step. Copy commands, code, and settings exactly. Fix a command only when the documentation shows the error, and say that you changed it.
- **Gaps:** if the video skips a step, add the step and mark it "(not in the video)".
- **Timestamps:** add the video timestamp to a step when the transcript has timestamps and a visual demo helps, for example `(12:40)`.
- **Sections 6 and 7:** skip a section only when it has no content. Keep the numbering of the other sections.
- **Tone:** plain and instructional in every section except *We're thinking*.
- **Length:** about 600–1500 words. Commands and code do not count. Shorter videos get shorter guides.
