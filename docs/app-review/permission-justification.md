# Permission justification — threads_keyword_search

## What the permission is used for

DaFeiYu Bot is a personal, non-commercial AI character account on Threads. The account posts short, clearly labeled AI-generated posts in the voice of a fictional "whale maid" character.

`threads_keyword_search` is used for one narrow purpose: to find recent **public** Threads posts that talk about a small set of topics the character is about (AI tools, white rice / food jokes, overwork, procrastination, and desktop pets), so the character can leave a relevant, non-promotional reply.

Without this permission, the Bot can only see its own posts and cannot participate in public conversations. It can still publish its own posts; this permission is only for discovery of public posts.

## How the permission is used

- Searches are limited to a short list of keywords (for example: `AI`, `白飯`, `摸魚`, `工程師`, `桌面寵物`).
- The Bot reads only public post text and username. It does not access private profiles, private messages, or non-public data.
- Before replying, the Bot checks the post against a blocklist (politics, religion, tragedy, medical, legal, financial advice, adult content, ads, links). Blocked posts are skipped.
- The Bot replies at most **10 times per day**, and never more than once to the same post.
- Replies are 1–2 sentences, in character, with no links, no promotion, and no requests to follow or click.
- Every reply is published through the official Threads API and carries Meta's AI-generated label.

## What the permission is NOT used for

- Not used to scrape profiles or build datasets.
- Not used to send unsolicited DMs (the app has no DM functionality).
- Not used for advertising, lead generation, or engagement farming.
- Not used to reply to political, religious, medical, legal, or financial content.
- Not used at high volume or in bursts.

## Data handling

- Only public post text and username are processed.
- Deduplication IDs and reply records are stored in the project's public GitHub repository for up to 60 days; per-person memory is removed after 180 days.
- Prompt text is sent to the AI provider in use (Groq, or optionally Google Gemini) only to generate the reply.
- No advertising, analytics, or selling of data.
- Users can request that the account stop replying to them, and can revoke access at any time.
- Public interactions (username, public comment text, reply) may be visible in the public repository; no non-public data is stored.

## Rate limits

- Maximum 10 public replies per day.
- Maximum 1 reply per post.
- Minimum 30 seconds between replies.
- The Bot stops immediately if the API returns a rate-limit or permission error.

## Why this benefits the community

The account is a small, clearly labeled AI character that participates in light, topical conversations. It does not impersonate a human, does not promote products, and does not mass-produce replies. The permission lets it join public discussions instead of only talking to itself.
