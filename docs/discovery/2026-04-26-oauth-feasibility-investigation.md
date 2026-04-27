# Consumer-subscription OAuth feasibility — Anthropic, OpenAI, Google

**Date:** 2026-04-26
**Status:** Discovery memo — input to vision-v6 §6.4 amendment decision
**Scope:** Whether each major LLM provider exposes a public OAuth flow that
lets a third-party application route inference through a user's existing
consumer subscription (Claude Pro/Max, ChatGPT Plus/Pro, Google AI
Pro/Ultra), with inference cost attributing to that subscription rather
than to a developer API key.

---

## 1. Executive summary

**No provider currently exposes the OAuth surface vision-v6 §6.4 assumes.**
Anthropic explicitly prohibits it as of February 2026 and enforces the
prohibition server-side as of April 4, 2026. Google has no public surface
and has actively blocked third-party tools that attempted to use Gemini
CLI OAuth tokens to route inference through Google AI Ultra subscriptions.
OpenAI's stance is the most permissive of the three — the Codex OAuth flow
is technically accessible to third parties and OpenAI executives have
publicly contrasted their position with Anthropic's — but no public OAuth
client registration program exists, the flow is scoped to the Codex
backend, and the third-party tools that use it explicitly disclaim
"personal development use only, not for commercial services, API resale,
or multi-user applications." For a hosted Phase-J product serving
non-technical authors with general-purpose (non-coding) workflows, none
of the three providers offers a sanctioned path.

The trend across the industry in Q1 2026 has been restrictive, not
permissive. Vision-v6 §6.4 needs amendment.

---

## 2. Per-provider findings

### 2.1 Anthropic — Conclusive NO

**Current state:** Anthropic's official Claude Code legal and compliance
page (https://code.claude.com/docs/en/legal-and-compliance) was updated
on February 19, 2026 with explicit language prohibiting the use of
consumer-subscription OAuth tokens in third-party tools:

> OAuth authentication is intended exclusively for purchasers of Claude
> Free, Pro, Max, Team, and Enterprise subscription plans and is
> designed to support ordinary use of Claude Code and other native
> Anthropic applications. […] Anthropic does not permit third-party
> developers to offer Claude.ai login or to route requests through
> Free, Pro, or Max plan credentials on behalf of their users.
> Anthropic reserves the right to take measures to enforce these
> restrictions and may do so without prior notice.

The prohibition is reinforced by Section 3.7 of the Consumer Terms of
Service (in place since February 2024), which forbids accessing the
Services "through automated or non-human means" except via an Anthropic
API Key. The February 2026 update closes the gap by explicitly naming
OAuth tokens and explicitly forbidding their use in third-party products
or services, including Anthropic's own Agent SDK.

**Enforcement timeline:**
- January 9, 2026 — Server-side block deployed (without notice) against
  third-party harnesses spoofing the Claude Code client.
- February 19–20, 2026 — Legal terms updated to formalize the prohibition.
- April 4, 2026, 12:00 PM PT — Subscription coverage of third-party tools
  fully terminated. Subscribers using OpenClaw, OpenCode, etc. through
  OAuth tokens must migrate to API key billing or per-token "extra usage"
  bundles.

**Sources:**
- Official: https://code.claude.com/docs/en/legal-and-compliance
- Coverage: https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/
- Coverage: https://venturebeat.com/technology/anthropic-cuts-off-the-ability-to-use-claude-subscriptions-with-openclaw-and-third-party-ai-agents/
- Coverage: https://winbuzzer.com/2026/02/19/anthropic-bans-claude-subscription-oauth-in-third-party-apps-xcxwbn/

**Caveats:** None. The prohibition is unambiguous, formally documented,
and actively enforced. The exact use case vision-v6 §6.4 contemplates
("Connect your Claude account") is the use case Anthropic is enforcing
against. Most recent signal: April 4, 2026 (enforcement cutoff).

---

### 2.2 OpenAI — No sanctioned path for the megálos use case

**Current state:** The picture is more nuanced than Anthropic's, but
arrives at the same answer for Phase J's specific shape.

**What does exist:**

The Codex CLI's "Sign in with ChatGPT" OAuth flow does authenticate
against ChatGPT Free, Plus, Pro, Business, and Enterprise subscriptions
and routes inference through them. Officially documented at
https://developers.openai.com/codex/auth, the flow is scoped to "the
Codex app, CLI, or IDE Extension." Codex is included in all paid ChatGPT
tiers (https://developers.openai.com/codex/pricing).

Third-party tools — OpenClaw, OpenCode, Cline, the community
`opencode-openai-codex-auth` plugin — have used this OAuth flow in
practice by reusing the Codex CLI's public OAuth client_id
(`app_EMoamEEZ73f0CkXaXp7hrann`) against the endpoint
`auth.openai.com/oauth/authorize`. The Codex backend serves not only
coding-specialized models (gpt-5.3-codex) but also general-purpose ones
(gpt-5.4, gpt-5.2), per the community `openai-oauth` proxy
(https://github.com/EvanZhouDev/openai-oauth) and Cline's documentation
(https://cline.bot/blog/introducing-openai-codex-oauth).

OpenAI executives have publicly contrasted their stance with Anthropic's.
OpenAI's Thibault Sottiaux (Codex engineering lead) has endorsed
third-party harness use of Codex subscriptions. OpenAI president Greg
Brockman and Sottiaux confirmed in September 2025 that GPT-5-Codex was
"developed to work in a variety of harnesses from Codex CLI to
third-party tools" (https://andrewmayne.com/2025/09/21/thoughts-about-openai-gpt-5-codex-from-my-conversation-with-greg-brockman-and-thibault-sottiaux/).

**Why this does not satisfy §6.4:**

1. **No public OAuth client registration program.** OpenAI does not
   publish a developer program that lets third parties register their
   own OAuth client with their own client_id, redirect URIs, or branded
   consent screen. Third-party tools reuse the official Codex CLI's
   client_id — a tolerated workaround, not a sanctioned program. The
   "Sign in with ChatGPT" feature OpenAI floated in May 2025
   (https://techcrunch.com/2025/05/27/openai-may-soon-let-you-sign-in-with-chatgpt-for-other-apps/)
   is positioned as identity-sharing (name, email, avatar) plus a small
   API-credit grant ($5 for Plus, $50 for Pro for 30 days), not
   subscription-routed inference. As of April 2026, eleven months later,
   no consumer-subscription inference-routing variant has launched.

2. **The Codex backend gates by system-prompt shape.** Per the
   community `openai-oauth` proxy documentation: "OpenAI's OAuth API
   requires a specific system prompt to validate Codex CLI authorization.
   Without this exact prompt format, API requests will be rejected even
   with valid OAuth tokens." A general-purpose workflow runtime like
   megálos would either have to spoof Codex-style system prompts (a
   compliance risk) or be denied at the API boundary.

3. **Third-party plugin authors explicitly disclaim commercial use.**
   The OpenCode-Codex auth plugin
   (https://github.com/numman-ali/opencode-openai-codex-auth) is
   explicit: "This plugin is for personal development use only.
   Not for: Commercial services, API resale, or multi-user applications.
   For production use, see OpenAI Platform API." The same restriction
   appears on the `openai-oauth` project: "Use only for personal, local
   experimentation on trusted machines; do not run as a hosted service,
   do not share access, and do not pool or redistribute tokens."
   Phase J is a hosted commercial service for multi-user audiences —
   exactly the use case these disclaimers exclude.

4. **The Apps SDK runs the wrong direction.** OpenAI's ChatGPT Apps
   SDK (https://developers.openai.com/apps-sdk/build/auth) lets
   third-party services be invoked *inside* ChatGPT — ChatGPT becomes
   the OAuth client, the third-party MCP server becomes the resource
   server, and the user's ChatGPT subscription pays for inference as
   normal. This is the inverse of what Phase J needs (Phase J wants to
   pull inference *out* to power its own UI, not embed itself inside
   ChatGPT's UI).

**Sources:**
- Official Codex auth: https://developers.openai.com/codex/auth
- Official Codex pricing: https://developers.openai.com/codex/pricing
- Official Apps SDK auth: https://developers.openai.com/apps-sdk/build/auth
- "Sign in with ChatGPT" reporting: https://techcrunch.com/2025/05/27/openai-may-soon-let-you-sign-in-with-chatgpt-for-other-apps/
- Community plugin (with disclaimer): https://github.com/numman-ali/opencode-openai-codex-auth
- Community proxy (with disclaimer): https://github.com/EvanZhouDev/openai-oauth
- Cline's third-party Codex OAuth: https://cline.bot/blog/introducing-openai-codex-oauth
- OpenAI exec endorsement of third-party harnesses: https://andrewmayne.com/2025/09/21/thoughts-about-openai-gpt-5-codex-from-my-conversation-with-greg-brockman-and-thibault-sottiaux/

**Caveats:** OpenAI has not formally prohibited third-party use of the
Codex OAuth flow in the way Anthropic has. There is plausible permissive
read of OpenAI's stance — namely, that for a coding-focused personal-use
tool the Codex OAuth flow is fair game. Phase J is neither coding-focused
nor personal-use. The path remains undocumented for megálos's specific
shape. Most recent signal: ~April 2026 (Codex auth docs current).

---

### 2.3 Google — Conclusive NO

**Current state:** Google has no public OAuth surface for routing
inference through consumer Google AI Pro or Google AI Ultra
subscriptions. The Gemini API's official OAuth flow
(https://ai.google.dev/gemini-api/docs/oauth) is configured at the
Google Cloud project level — billing flows through the developer's GCP
project, not through the user's consumer subscription. Functionally
this is an API-key-equivalent path with extra friction, not the
consumer-subscription onramp vision-v6 §6.4 contemplates.

Google's actual answer to bridging consumer subscriptions and developer
use was announced January 27, 2026
(https://blog.google/innovation-and-ai/technology/developers-tools/gdp-premium-ai-pro-ultra/).
Google AI Pro and Ultra subscribers now receive monthly Google Cloud
credits ($10/month for Pro, $100/month for Ultra) that can be applied
to a GCP billing account to call the Gemini API. The user still
provisions a Cloud project, configures billing, and effectively pastes
credit-backed credentials into third-party apps. This is not a
consumer-subscription onramp — it is a credit subsidy for the
developer-API path.

**Enforcement against third-party use of Gemini CLI OAuth:**
February 2026, Google blocked Google AI Ultra subscribers who used
OpenClaw and similar third-party tools that piped Gemini CLI's OAuth
tokens (from the Antigravity OAuth flow) into external workflows.
Affected users reported 403 errors, account restrictions, and in some
cases blocks extending to other Google services (Gmail, Workspace) —
all while subscriptions continued to be billed.

**User-side feature requests are open and unanswered:**
- GitHub: https://github.com/google-gemini/gemini-cli/issues/21866
  (March 10, 2026 — "Google AI Ultra Subscription OAuth Support for
  OpenClaw") — open, marked priority/p2, no Google response.
- Google AI Developer Forum:
  https://discuss.ai.google.dev/t/can-google-ai-ultra-be-used-with-openclaw-via-oauth/130360
  (March 10, 2026) — open, no Google response.

A March 25, 2026 Google announcement
(https://github.com/google-gemini/gemini-cli/discussions/22970) signals
further tightening: "Starting March 25, 2026, we're changing the way
Gemini CLI routes traffic with higher priority given to accounts based
on license type and account standing." This is more restrictive, not
more permissive — the trajectory matches Anthropic's.

**Sources:**
- Official Gemini API OAuth (Cloud-scoped): https://ai.google.dev/gemini-api/docs/oauth
- Google's GDP-in-AI-subscription bundling (the actual answer): https://blog.google/innovation-and-ai/technology/developers-tools/gdp-premium-ai-pro-ultra/
- Coverage of OpenClaw blocks: https://www.analyticsinsight.net/news/google-restricts-gemini-ai-ultra-accounts-over-openclaw-oauth-access
- Coverage of OpenClaw blocks: https://www.trendingtopics.eu/google-blocks-paying-ai-subscribers-using-third-party-openclaw-tool/
- Open feature request: https://github.com/google-gemini/gemini-cli/issues/21866
- Service-update discussion (further tightening): https://github.com/google-gemini/gemini-cli/discussions/22970

**Caveats:** Google's restrictive language is in enforcement actions and
support pages, not yet in formal terms-of-service text equivalent to
Anthropic's. The intent is unambiguous; the contractual articulation is
less explicit than Anthropic's. Most recent signal: March 25, 2026
(traffic prioritization change).

---

## 3. Implications for vision-v6 §6.4

The investigation falls into the third sub-case in the brief: no
provider exposes the OAuth surface as drafted. The recommendation is
amendment of vision-v6 §6.4. Per the brief's instruction not to redesign
the Shape 5 onramp inside this memo, I am restricting the recommendation
to a one-line pointer.

**Recommended amendment language for vision-v6 §6.4:**

> The consumer-subscription onramp described above (e.g., "Connect your
> Claude account" / "Connect your ChatGPT account") is not currently
> supported by any of the three major LLM providers and is removed from
> v6's commitments. As of April 2026: Anthropic explicitly prohibits
> third-party use of consumer OAuth tokens; Google has no public surface
> and actively enforces against third-party tool use of Gemini CLI OAuth;
> OpenAI's Codex OAuth flow is technically accessible but is officially
> scoped to coding tools and explicitly disclaimed by third-party
> implementations as not for commercial multi-user services. Phase J
> ships with API-key BYOK as the sole onramp until the provider landscape
> changes. The Shape 5 audience claim is correspondingly narrowed; see
> follow-on strategic conversation for redesign options.

This is intentionally a one-line pointer, not a redesign.

The downstream consequence — that Shape 5's "bring your consumer
account" promise is broken and that Phase J's value proposition against
Landbot weakens because API-key paste is technical friction non-technical
users may not tolerate — is exactly the consequence the
phase-j-scaffold §7 open question 1 already named. The open question is
now answered in the negative.

The strategic conversation that follows from this is: given that
consumer-subscription OAuth is not viable in 2026, is Phase J still
worth doing on API-key-only economics, or does the Shape 5 ambition
get deferred until provider behavior changes? That is a separate
conversation, not part of this memo's scope.

---

## 4. Open uncertainties

The following could not be definitively resolved within this
investigation:

**For Anthropic — none.** The prohibition is explicit, documented in
official terms, and actively enforced. The investigation closes here as
conclusive.

**For OpenAI:**

- I did not find explicit terms-of-service language from OpenAI saying
  third-party hosted services cannot use Codex OAuth. The prohibition is
  inferred from (a) the structural absence of an OAuth client
  registration program, (b) the system-prompt gate on the Codex backend,
  (c) self-disclaimers from third-party tool authors, and (d) the
  scope-restriction language in OpenAI's own Codex auth docs ("for the
  Codex app, CLI, or IDE Extension"). This is suggestive and
  multiply-supported, but not as airtight as Anthropic's explicit
  prohibition. *Possible follow-up:* read OpenAI's full Service Terms
  and App Developer Terms more carefully for any language addressing
  third-party use of subscription OAuth — a 30-minute exercise.
- The "Sign in with ChatGPT" feature announced May 2025 has not launched
  as a subscription-routed inference feature. Whether it ever will is
  undocumented. The investigation reports this as a signal, not a
  forecast.
- The OpenClaw/OpenCode tolerance pattern could change. OpenAI tolerated
  this through April 2026; nothing prevents an Anthropic-style policy
  shift in future months.

**For Google:**

- Google's restrictive position is documented through enforcement actions
  and unanswered feature requests, but the explicit terms-of-service
  language is less crisp than Anthropic's. The intent is unambiguous;
  the contractual articulation is partial. *Possible follow-up:* check
  whether the March 25, 2026 service-update announcement was followed by
  a formal terms revision.

**Cross-provider:**

- Q1 2026 has been a uniformly restrictive quarter (Anthropic January
  block → February terms update → April enforcement; Google February
  enforcement; OpenAI no formal change but increasing scrutiny). It is
  possible — but not predictable — that this trajectory reverses if
  competitive dynamics shift. The brief explicitly says not to
  extrapolate from such signals, and I have not.

---

## 5. Methodology notes

- Roughly two and a half hours of focused research.
- Primary sources: provider official documentation and policy pages
  (preferred over secondary reporting where both available).
- Secondary sources: tech press coverage (The Register, VentureBeat,
  TechCrunch, MediaNama) used for timeline confirmation and to surface
  events that may not yet appear in official documentation.
- Tertiary sources: third-party tool documentation (OpenClaw, OpenCode,
  Cline) and community plugins (numman-ali, EvanZhouDev), used as
  positive evidence for what OAuth surfaces are technically usable in
  practice and as evidence of the self-imposed scope restrictions
  third-party authors apply.
- The investigation explicitly avoided extrapolation from "coming soon"
  signals (per brief).
- The investigation explicitly avoided proposing alternative onramps
  (per brief).

```
