# GEO System — How AI Search Works and How to Get Recommended

Built from 10 transcribed videos in `GEO-Research/transcripts/` (files 001, 003–012).
GEO = Generative Engine Optimization. Same thing as AEO (Answer Engine Optimization), AIO, or LLMO.
Goal: get your brand **mentioned, cited and linked** when people ask ChatGPT, Gemini, Perplexity, Claude, Copilot or Google AI Overviews / AI Mode.

---

## Part 0 — Which videos show real proof (weighting)

Each video is scored on the evidence it actually shows, not on how confident it sounds. When videos disagree, the higher tier wins.

| Tier | Video | Proof shown | Weakness |
|---|---|---|---|
| **A — Hard data** | **007 / 011 / 012 / 009 Ahrefs** | Large studies: 174,000 cited pages (length doesn't matter), 75,000 brands (mentions 0.664), 140M sites (5.9% block GPTBot). A **controlled experiment**: a fake brand was planted to test misinformation. Real business results: AI visitors convert 23× better. Says openly what is *not* proven (schema, llms.txt). | Promotes Ahrefs tools. The figures are correlations, not proof of cause. |
| **B — Live demos + cited research** | **004 Exposure Ninja** | Shows real ChatGPT and Perplexity answers on screen: fan-out queries, cited sources. Client cases: Zugu recommended with and without web search, The Ordinary = "best value". Cites the peer-reviewed GEO paper (+40% from stats, quotes and citations). | An agency selling GEO. Only successes are shown. |
| **B — Own result, shown live** | **010 Hasan Aboul Hasan** | Shows **his own course ranking #1** in ChatGPT, Claude and Perplexity for a real prompt. Built a working tracker (180 brand mentions logged). Real stress-test page that got cited. | One website. No before/after numbers. Says himself "not 100% guaranteed… still testing". |
| **C — Quotes others' studies** | **003 OMNIUS** | Third-party numbers: SparkToro (Google +21.6%), a Search Engine Journal study of 40,000 responses (citations per platform), 87% Bing overlap for ChatGPT. | No experiment or client result of its own. Data is from early 2025. |
| **D — Advice, no proof** | **001 Helena Liu** | Clear steps and weak/strong writing examples. | The examples are made up. The "60% of consumers" stat has no source. **Admits her own AI traffic is "not doing so hot".** |
| **D — Tool demo** | **006 Britx Sui** | Shows the Semrush AI-visibility screens. | Sponsored. Her own site scores "low". No improvement shown. |
| **D — Opinion** | **005 Amir Rasheed**, **008 MarkeTech (Hindi)** | General SEO + GEO advice. | No data, demos or results. |

**How this changes the system:**
- **Trust most (Tier A + B agree):**
  - Brand mentions across the web.
  - YouTube presence.
  - Freshness.
  - Stats, quotes and sources in your content.
  - Listicle and comparison formats.
  - Ranking in Google *and* Bing.
  - Making sure AI crawlers aren't blocked.
- **Lower priority (backed mainly by Tier D):**
  - Schema / JSON-LD as a "ranking boost". Ahrefs found no proof.
  - llms.txt. No provider uses it.
  - Huge FAQ schema on every page.
  - Long word counts. Tier A proved length doesn't matter.
- **Proof you can get yourself:** the prompt-tracking in Stage 5 is the only proof that counts for *your* brand. Measure before and after every change.

---

## Part 1 — How AI search actually works

### 1. AI answers come from two places
| Source | What it is | How you influence it |
|---|---|---|
| **Training data** | A frozen snapshot of the internet (websites, Reddit, YouTube transcripts, books). Updated roughly every ~6 months. | Be mentioned **widely and consistently** across the web so the model "learns" your brand. |
| **Live retrieval (RAG)** | For fresh or specific questions, the AI runs web searches, reads the pages, then writes an answer. | Rank in the search results the AI uses (Google, and Bing for ChatGPT), with content that is easy to quote. |

Sources: Ahrefs (007, 011), Exposure Ninja (004).

Example: ChatGPT recommended Zugu iPad cases **without searching**. It already knew the brand from training data. For other questions it searched and cited Wired and Reddit pages that mention Zugu (004).

### 2. Query fan-out: one question becomes many searches
The AI splits one prompt into many smaller sub-searches. "Plan a 5-day Japan trip" becomes "best Tokyo neighbourhoods", "Kyoto November weather", "JR Pass worth it", and so on.
- An average prompt triggers **9–11 sub-queries**, and up to 28. Deep research mode ran **420** for one question (011).
- **What this means:** one page for one keyword is not enough. You need to **cover the whole topic**, so you match many of those sub-searches.
- Fan-out queries are random and have no search volume. Treat them as clues about which subtopics matter, not as a keyword list (011).

### 3. Results are probabilistic, not a fixed ranking
Ask the same question 5 times and you may be cited 3 times. There is no "#1 position", only a **share of answers** ("AI visibility" / "share of voice") (011).

### 4. Every platform prefers different sources
Only **7 of the top 50** cited domains appear across all three of AI Overviews, ChatGPT and Perplexity (007).

| Platform | Prefers | Notes |
|---|---|---|
| **ChatGPT** | Big publishers & media (Reddit, Wikipedia, Forbes, Business Insider, Wired, G2, Gartner, LinkedIn) | Uses **Bing**. ~87% of citations match Bing results (003). Only 8–10% overlap with Google top 10. Has paid deals with some publishers (004). Can't read JavaScript. |
| **Google AI Overviews** | Authoritative sites, YouTube, Reddit | YouTube = ~5.6% of all citations. Overlap with the Google top 10 fell from 76% to ~38% (007). |
| **Google AI Mode** | YouTube (#1 by far), Wikipedia, Quora, Facebook/Instagram | Only 13.7% source overlap with AI Overviews (007). |
| **Perplexity** | Closest to Google rankings, YouTube | 28.6% of citations rank in the Google top 10. Gives a link most often (52%) (007). |
| **Gemini** | Medium, Reddit, YouTube | (003) |

### 5. Three kinds of "visibility"
1. **Cited + linked**: the user can click to you. Only **~28%** of mentions include a link (007).
2. **Mentioned, not linked**: word-of-mouth at scale. The user often googles you later.
3. **Not visible**: the gap you need to fix.

Unlinked mentions still matter: they teach the model "your brand = this topic" (007).

---

## Part 2 — What makes AI pick you (ranking signals)

Strongest evidence first. "Strong" = backed by data in the videos. "Mixed" = videos disagree.

| Signal | Evidence | What the data says |
|---|---|---|
| **Brand mentions across the web** | Strong | Branded web mentions correlate **0.664** with AI Overview visibility, more than backlinks or domain rating. Mentions on *highly linked* pages: **0.70** (007). |
| **YouTube presence** | Strong | YouTube mentions correlate **0.737** with ChatGPT visibility, the strongest factor Ahrefs studied (007). |
| **Classic SEO ranking** | Strong | SEO is the foundation (all videos). Ranking in Google → AI Overviews / Perplexity. Ranking in **Bing** → ChatGPT (003, 004). |
| **Freshness** | Strong | AI-cited pages are ~26% fresher. **76%** of ChatGPT's top-cited pages were updated in the last 30 days (012). |
| **Statistics, quotes, cited sources** | Strong | GEO research paper: **+40% visibility** (004). Specific numbers beat vague claims (001, 010). |
| **Format: listicles / comparisons / "best X"** | Strong | **43.8%** of ChatGPT-cited pages are listicles (012). Comparison tables work too (010). |
| **Consensus** | Strong | Many sources saying the same thing about you → AI repeats it (011). |
| **First-hand experience** | Medium | A personal blog about installing a heat pump decided ChatGPT's #1 manufacturer recommendation (004). |
| **Content length** | ❌ Doesn't matter | Correlation 0.04. Over half of cited pages are under 1,000 words (012). |
| **Schema / JSON-LD** | Mixed | Helena Liu (001) and Hasan (010) push it hard. Ahrefs (009) says there's no proof it helps AI citations: "doesn't hurt, don't over-invest". |
| **llms.txt** | ❌ Not used | No major AI provider officially reads it yet (009). |

---

## Part 3 — The system (5 stages)

### Stage 1 — Access: make sure AI can read you (one-time, ~1 hour)
1. Open `yourdomain.com/robots.txt` and make sure these are **not** disallowed: `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`.
   ⚠️ Cloudflare's "Instruct AI bot traffic" setting is **on by default** and may block them (009).
2. **JavaScript test:** turn off JavaScript in your browser and load your site. If the content disappears, ChatGPT can't see it. Fix it with server-side rendering (009).
3. **Speed:** slow pages get dropped during live retrieval (009).
4. **Clean HTML:** one H1, logical H2/H3s, one idea per paragraph (009).
5. Submit your site to **Bing Webmaster Tools** as well as Google Search Console (003, 004).
6. Optional: add FAQ / Article / Product / LocalBusiness schema (JSON-LD). AI can generate it from the page text (001, 010).
7. Redirect "hallucinated" URLs: AI sends visitors to 404 pages 2.87× more often than Google. Find 404s with AI referrers and redirect them (009).

### Stage 2 — Baseline: find out where you stand now (one-time, then monthly)
1. **Map your entities:** brand name, product names, founder or personal brands, and the features you own (007).
2. **Write your "known for" statement:** what AI should say about you, e.g. "best value", "for beginners" (004, 007).
3. **Build a prompt list:** 20–50 real questions customers would ask AI. Write them as full sentences, not keywords (010, 007).
4. Ask each prompt in ChatGPT, Gemini, Perplexity and Google AI Mode. Record:
   mentioned? linked? which competitors? which sources were cited? is the description accurate?
5. **Score the 6 gaps** (007):
   | Gap | Question |
   |---|---|
   | Visibility | Do competitors appear more often than us? |
   | Narrative | Does AI describe us the way we want? |
   | Topic | Which topics should link to us but don't? |
   | Format | Are competitors cited with videos, comparisons or reviews that we don't have? |
   | Web mentions | Which listicles, review sites or forums mention competitors but not us? |
   | Demand | Which searches in our space never show our name? |

### Stage 3 — On-site content: become the easiest source to quote (ongoing)
**Writing rules** (012, 001, 008):
- **Answer first (BLUF):** start every section with the direct answer, then explain.
- **Each section stands alone:** AI cuts pages into chunks. Every H2 section must make sense on its own, so write "Acme's pricing starts at $20", not "our pricing".
- **Name things (entity-rich writing):** "Ahrefs Keywords Explorer finds low-difficulty keywords", not "this tool helps with SEO".
- **Short, simple sentences** with one idea each.
- **Add proof:** statistics, expert quotes, named sources (HBR, Gartner, government data), and your own test results.
- **Human tone and real experience:** don't publish raw AI-written text (008).

**Pages to create:**
- An **FAQ page** plus an FAQ section on key pages, built from real customer questions (001, 005, 010).
- **"Best X" / "X vs Y" / comparison tables** for your category (010, 012).
- **Original data:** surveys, tests and benchmarks that AI can cite (010, 012).
- **Branded frameworks:** give your ideas a name ("the [Brand] Method") so AI credits you instead of absorbing the idea (012).
- **Official facts page:** specific numbers, dates, founders and pricing. AI prefers "specific fiction" over "vague truth", so fill every information gap yourself (007).

**Keep it fresh:**
- Update your top 5–10 pages every month with real changes (new stats, examples). Don't just change the date (012).
- Show the "last updated" date on the page (010).
- Refresh "sleeper pages": old pages with backlinks whose traffic has dropped (012).

### Stage 4 — Off-site: get mentioned where AI reads (ongoing, biggest lever)
**Tier 1 — Third-party editorial** (hardest, most valuable)
- Get onto the "best X" listicles, review sites and comparison posts that AI already cites for your prompts (from Stage 2).
- Trade publications in B2B: often easy, because they need content (004).
- Digital PR.

**Tier 2 — Communities / user-generated content**
- **Reddit, Quora, niche forums.** Give genuine answers in threads where your product truly fits. Don't spam (007, 010).
- **Review sites:** G2, Trustpilot, Google reviews, Capterra (001, 003).
- Wikipedia, if you're genuinely notable (005).

**Tier 3 — Your own channels**
- **YouTube** (the strongest single factor):
  - Choose "search hit" topics, not viral ones.
  - Put the exact keyword in the title.
  - Write a real summary in the description.
  - Add timestamps.
  - **Say the keyword out loud** in the video.
  - Match the format that already ranks (007).
- **LinkedIn and Medium articles:** AI crawls these. Instagram and TikTok are mostly behind logins, so they help little (001, 003).
- Repurpose each piece of content onto 3–4 platforms every week, so the same facts appear in many places (010).

### Stage 5 — Measure and repeat
**Three ways to track** (007):
1. **AI referral traffic:** in GA4, create an "AI traffic" channel. Admin → Data display → Channel groups → source matches a regex like
   `chatgpt\.com|perplexity|gemini\.google\.com|copilot\.microsoft\.com|claude\.ai|deepseek\.com`
   This undercounts, because some apps hide the referrer.
2. **AI bot visits:** server logs or Cloudflare. The pages bots hit often are your likely citation sources.
3. **"How did you hear about us?"** Add "ChatGPT / AI assistant" as an option at signup or checkout. This is the most important way to prove value.

**Prompt tracking:** re-run your Stage 2 prompt list on a schedule and record mentioned / linked / competitors. You can do this by hand, with paid tools (Ahrefs Brand Radar, Semrush One, etc.), or with your own script. Hasan built a free one with Make plus the OpenAI search API (010).

**Cadence:**
| When | Do |
|---|---|
| Weekly | Publish or repurpose content on 3–4 platforms. Answer 2–3 relevant Reddit or Quora threads. |
| Monthly | Re-run the prompt list. Check share of voice, new citing domains, topic gaps and accuracy. Refresh your top pages. |
| Quarterly | Do a full competitor gap audit (Stage 2) and reset priorities. |

**Prioritise each gap as one of three types** (007):
- **Fix:** improve an existing page. Fastest.
- **Build:** create a new page or video.
- **Influence:** outreach or PR to get mentioned elsewhere.

---

## Part 4 — Keep in perspective
- **AI traffic is still small:** ~0.25% of an average site's traffic, and Google sends ~210× more. But it **converts much better** (23× at Ahrefs) because AI has already "pre-sold" the visitor (007). ChatGPT traffic grew ~9.7× in a year.
- **SEO isn't dead.** Every video agrees that GEO sits **on top of** SEO (003, 005, 007, 008). Do both.
- **No guarantees:** results vary run to run and change every few days. Over 45% of AI Overview citations change on each refresh, which happens about every 2 days (007, 010).
- **Watch for misinformation:** Ahrefs planted fake facts about a made-up brand, and Gemini and Perplexity repeated them 37–39% of the time. Monitor what AI says about you and correct it on your own site first (007).
- **Sales bias in the sources:** 004 and 003 are agencies selling GEO services. 006 is sponsored by Semrush and 010 by Make. Ahrefs (007, 009, 011, 012) promotes its own tools, but gives the most data and is the most careful about what isn't proven.

---

## Source videos
| # | Title | Channel |
|---|---|---|
| 001 | How to Get ChatGPT to Recommend Your Business | Helena Liu |
| 003 | Generative Engine Optimization – How to Rank on ChatGPT & Perplexity | OMNIUS |
| 004 | How To Rank in ChatGPT (with REAL Examples) | Exposure Ninja |
| 005 | Why You Need to Learn GEO Right Now (Hindi/Urdu) | Amir Rasheed |
| 006 | The New SEO: How to Rank in ChatGPT, Claude & Other AI Tools | Britx Sui |
| 007 | Complete AI SEO Course for Beginners (86 min) | Ahrefs |
| 008 | SEO vs AEO vs GEO (Hindi) | MarkeTech by Chandan |
| 009 | Technical SEO for AI: Robots.txt, GPTBot & llms.txt | Ahrefs |
| 010 | How To Get Free Traffic From ChatGPT (AIO Course) | Hasan Aboul Hasan |
| 011 | How AI Search Engines Work | Ahrefs |
| 012 | How to Optimize Content for AI Search Engines | Ahrefs |

Note: 011, 012 and 009 are lessons from the full Ahrefs course (007), so their content overlaps.
