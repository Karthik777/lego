---
slug: vedicreader-what-it-does
title: VedicReader, word by word
summary: A browser app for Vedic texts. Audio synchronized line by line, eight Indic scripts on the fly, word meanings inline without leaving the verse, and a ritual guide that tells you what to bring.
visibility: public
author_name: Karthik
---

The first version was a plain HTML file. The Vallabha MahaGanapathi Trishati in Devanagari. I used it every morning. It worked.

The texts I actually wanted to read are longer. The Rudram runs to pages. Reading a mantra without knowing what any of the words mean is repetition. 
That is not nothing, but it is less than what it could be.

VedicReader is at [vedicreader.com](https://vedicreader.com).

## Text and meaning together

![Text view with Devanagari and word-by-word meanings](meaning.png)

Every text in the database is stored as anuvakas(sections), each with a canonical Sanskrit form, its IAST transliteration, and a plain-language meaning.
When you open a text you see the full verse. 

Sections also carry full meanings and word-by-word etymologies, accessible as expandable blocks below each section.

## Eleven scripts

![Script selector with eight Indic scripts](lang.png)

The script selector covers Devanagari, Telugu, Kannada, Tamil, Malayalam, Bengali, Gurmukhi, Grantha, Harvard-kyoto, Itrans and Iast. 
The database stores Sanskrit in Devanagari. Transliteration happens server-side for the moment. It'll be ported to the client eventually.

This matters because different traditions read the same texts in different scripts. A Tamilian reading the Rudram knows it in Tamil or Grantha, not Devanagari. 
The texts are already hard.

## Audio, synchronized

![Japa mode with synchronized playback](japa.png)

Each text has an associated audio file. Playback is line-by-line: as the audio advances, the current line highlights and 
the display scrolls to keep it visible. You can tap any line to seek directly to it.

Japa mode handles repetitive practice. You set a count: 1, 108, or infinite loop. The bead counter advances each time a cycle completes. 
You can follow the audio or mute it and chant yourself.

## Ritual guidance

![Ritual tier selection with materials and duration](ritual.png)

Some practices involve a sequence of steps, specific mantras at each step, and materials you need to have ready. VedicReader has a ritual guide that covers all of that.

Each ritual has two or three tiers. Tier 1 is abbreviated, Tier 3 is the full version. Selecting a tier gives you the estimated duration, the materials list with checkboxes, and the step-by-step sequence with the associated texts linked inline.

## Search

![Search results grouped by category with keyword matches highlighted](search.png)

Search runs across all categories simultaneously: shlokas, mantras, stotras, japas. Short keyword queries use FTS5. 
Queries that look like questions (what is the meaning of, significance of) go to the vector index instead. 
Results are grouped by category with the matching line shown in context.


---

The stack is FastHTML, MonsterUI, SQLite with litesearch for search, and a small amount of JavaScript for audio. 
The transliteration engine and audio sync are the two hardest parts. Everything else is just data plumbing.
