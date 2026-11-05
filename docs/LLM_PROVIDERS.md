# Which LLM provider to use

Checked 4 November 2026. Prices change, so confirm them when you sign up. Switching needs only a `.env` change (see [AGENT.md](AGENT.md)).

## Decision

**Gemini, decided on 4 November 2026:** the free tier now, and the paid tier later. It's one provider, so moving to paid needs no code or setup change, and it can be paid by UPI.

| When | Use | Why |
|---|---|---|
| **Now, free** | **Gemini free tier** | A free tier on many models. Use it for development only, because Google may use free-tier data to improve its products |
| **Later, paid** | **Gemini paid tier** | Paid data isn't used to improve Google's products. Pay by UPI: the first payment is at least ₹1,000 |

**Which Gemini models** is still open, because price varies a lot. Run the answer tests on the cheaper and stronger models, then read the answers.

**Sarvam 105B is the one to compare against** if Gemini's Indian-language answers disappoint. It's built for Indian languages, bills in rupees, and its ₹100 of free credit covers our tests.

## Setting them up

Gemini, in `.env`:

```
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_API_KEY=your-key
LLM_MODEL_PLAN=gemini-3.5-flash-lite,gemini-3.1-flash-lite
LLM_MODEL_COMPOSE=gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash-lite
LLM_REASONING=gemini-3.8-flash:none,gemini-3.6-flash:none
```

**What testing this key showed (4 November 2026):**
- **Gemini 2.5 Flash-Lite isn't available:** it's on the price list, but returned "no longer available to new users". So 3.1 Flash-Lite is the cheapest option for this key.
- **Models are often busy:** 3.1 Flash-Lite, 3.7 Flash and 3.8 Flash each returned "high demand" at times. The engine now tries the next model, so a question may be answered by a different model than the first listed.
- **Hidden thinking costs far more than it looks:** on one short question, 3.6 Flash used 574 tokens by default, 386 on `low` and 52 on `none`, for an answer of about the same length. It's billed as output. We start with `none`, and raise it if answers suffer.
- **Not every model accepts `none`:** 3.5 Flash-Lite rejected it, so `LLM_REASONING` is set per model. It used 69 tokens with no setting.
- **JSON mode works** on the models that responded, so no code change was needed.
- **Speed:** 3.5 Flash-Lite took about 9 to 14 seconds even on tiny requests, on a busy day.

Sarvam, if comparing, in `.env`:

```
LLM_BASE_URL=https://api.sarvam.ai/v2
LLM_API_KEY=your-key
LLM_MODEL_PLAN=sarvam-105b
LLM_MODEL_COMPOSE=sarvam-105b
```

**Still to test on Sarvam, if comparing:**
- **Reasoning tokens:** these are billed as output, so its reasoning setting affects cost. The engine doesn't set it yet.
- **Model names:** taken from the providers' pages, but check them in the console.

## Prices

Per million tokens. Dollar prices are converted at about ₹90, which is my assumption.

| Model | Input | Output | Free tier? | Source |
|---|---|---|---|---|
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 | Listed, but not offered to new users | [Google](https://aistudio.google.com/docs/pricing) |
| Gemini 3.5 Flash-Lite | $0.30 | $2.50 | Yes | [Google](https://aistudio.google.com/docs/pricing) |
| Sarvam 105B | ₹15 | ₹60 | ₹100 credit | [Sarvam](https://www.sarvam.ai/api-pricing) |
| Groq gpt-oss-120b | $0.15 | $0.60 | Yes, what we use now | Third-party trackers such as [this one](https://www.morphllm.com/groq-pricing). Groq's own page didn't show prices when fetched |
| DeepSeek Flash | $0.15 off-peak, $0.30 peak | $0.60 off-peak, $1.20 peak | Unclear | [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing) |
| Gemini 3.1 Flash-Lite | $0.25 | $1.50 | Yes | [Google](https://aistudio.google.com/docs/pricing) |
| Gemini 3.8 Flash | $0.75, then $1.50 from January 2027 | $3.75, then $7.50 | Yes | [Google](https://aistudio.google.com/docs/pricing) |

**Free-tier limits:**
- **Groq:** on our key, 8,000 tokens a minute and 200,000 a day per model, measured when calls hit the limit. A full deep answer doesn't fit in one minute's allowance, and only a few fit in a day.
- **Gemini:** Google shows these only inside AI Studio, so check there.

## What a question would cost

Token use is from real runs on Groq's models, not yet on Gemini. I assumed 90% input and 10% output, because most of it is evidence going in, and that hidden thinking is off.

| Question | Tokens | 3.1 Flash-Lite | 3.5 Flash-Lite | 3.8 Flash to December | 3.8 Flash from January | Sarvam 105B |
|---|---|---|---|---|---|---|
| Quick, exact records | About 2,000 | ₹0.07 | ₹0.09 | ₹0.19 | ₹0.38 | ₹0.04 |
| Standard | About 10,000 | ₹0.34 | ₹0.47 | ₹0.95 | ₹1.89 | ₹0.20 |
| Deep, measured | Up to about 41,000 | ₹1.38 | ₹1.92 | ₹3.87 | ₹7.75 | ₹0.80 |
| Deep, full evidence | About 80,000, my estimate | ₹2.70 | ₹3.74 | ₹7.56 | ₹15.12 | ₹1.56 |

A real setup would plan and judge on a cheap model and write on a stronger one, so it would land between these columns.

- **Limits of these numbers:** the deep figures come from three runs with evidence cut to fit the free tier. Rewrites, translations and reasoning tokens add to them. Prompt caching reduces them.
- **Running our tests:** 20 deep questions at 80,000 tokens each come to about ₹31 on Sarvam, so the ₹100 credit covers it.
- **A real month on Sarvam:** assume half quick, 35% standard and 15% deep questions, which averages about ₹0.32 a question. That's about ₹960 a month at 100 questions a day, or about ₹9,600 at 1,000 a day.

## A free backup when Gemini runs out

Gemini's free tier allows 500 requests a day per model, as hit on 5 November 2026. Adding `groq:` before a model name in `LLM_MODEL_PLAN` or `LLM_MODEL_COMPOSE` sends it to Groq using `GROQ_API_KEY`, so the engine moves on to it when the earlier models fail:

```
LLM_MODEL_PLAN=gemini-3.5-flash-lite,gemini-3.1-flash-lite,groq:openai/gpt-oss-20b
LLM_MODEL_COMPOSE=gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash-lite,groq:openai/gpt-oss-120b
```

- **Limit:** `gpt-oss-120b` reported 1,000 requests a day and 8,000 tokens a minute on the free tier, which is too small for large deep answers. The engine's existing handling for a request that's too large applies.
- **Measuring:** different models give different quality, so compare test runs only when they used the same models. The trace records each call's model.

## One model for everything, or a mix

The engine can use a cheap model for planning and judging, and a stronger one for writing and checking. Using one model for every step costs this much. The same assumptions apply, and the mix assumes about 35% of tokens go to the cheap model, which is my estimate.

| Setup | Standard question | Deep question, full evidence | A month at 100 questions a day |
|---|---|---|---|
| Claude Haiku 5.5 only | ₹0.13 | ₹1.01 | ₹620 |
| Gemini 3.1 Flash-Lite only | ₹0.34 | ₹2.70 | ₹1,670 |
| **Mix: 3.1 Flash-Lite and 3.8 Flash, to December** | **₹0.73** | **₹5.86** | **₹3,630** |
| Gemini 3.8 Flash only, to December | ₹0.94 | ₹7.56 | ₹4,680 |
| **Mix: 3.1 Flash-Lite and 3.8 Flash, from January** | **₹1.35** | **₹10.77** | **₹6,670** |
| Gemini 3.8 Flash only, from January | ₹1.89 | ₹15.12 | ₹9,360 |
| Claude Sonnet 5.5 only | ₹2.52 | ₹20.16 | ₹12,470 |
| Claude Opus 5.5 only | ₹5.04 | ₹40.32 | ₹24,950 |
| Claude Fable 5.1 only | ₹12.60 | ₹100.80 | ₹62,370 |

- **Prices:** [Anthropic](https://platform.claude.com/docs/en/about-claude/pricing) and [Google](https://aistudio.google.com/docs/pricing). OpenAI's page refused the fetch, so it isn't included.
- **Quality isn't measured** for any of these on our questions, so price is all this table shows. A bigger model may be worth it for the writer alone.
- **Claude Haiku 5.5** is the cheapest here, and it's untested. Payment by UPI isn't checked for Anthropic.
- **Asking a model directly, with no documents,** costs under ₹1 for a short answer. It isn't comparable: it can't see this state's current orders, and it has no sources to check against.

## Paying with UPI

**Gemini works with UPI.** The billing screen on this account offers a UPI QR code for buying credits (seen 4 November 2026). The terms it shows:

- **Minimum first payment:** ₹1,000 on this account. The box starts at ₹2,500, so lower it if you only want the minimum.
- **Non-refundable:** credits can't be refunded, except as Google's credit terms allow.
- **Use and expiry:** they only work with the Gemini API, and they expire a year after purchase.
- **Auto-reload:** off in that screen. Leave it off, so spending can't grow by itself.

**What ₹1,000 buys,** at the estimated full-evidence deep question: about 370 on Gemini 3.1 Flash-Lite, or about 65 on Gemini 3.8 Flash at its January price.

| Other providers | What's known |
|---|---|
| **Sarvam** | Bills in rupees, with credits added under Settings → Billing. [Its docs](https://docs.sarvam.ai/api/platform/faq) don't list payment methods, so check there |
| **Groq, DeepSeek** | No evidence of UPI found |
| **Resellers** | Some third-party services advertise UPI and pass requests on to other models. I wouldn't send citizens' questions through a reseller without checking who handles the data |

## Privacy

- **Gemini free tier:** [Google lists](https://aistudio.google.com/docs/pricing) this data as used to improve its products, and paid-tier data as not. Don't use the free tier for real citizens.
- **Sarvam:** owners can [turn off model training](https://docs.sarvam.ai/api/platform/faq) and set how long data is kept. Its docs don't say where API data is stored, so ask before launch.
- **DeepSeek:** its pricing page doesn't say where data is processed, so check before using it for a government-facing service.
- **In every case:** the engine hides long ID-like numbers before anything reaches a model.
