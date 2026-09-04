# Canonical transcript extraction: SMF inputs, lookbacks, and thresholds

Source: `C:\Users\satta\Downloads\NoteGPT_Transcript_How To Track Smart Money Footprint In Indian Stock Market  Proper Step By Step Video.txt`  
SHA-256: `818dc042fdf51d77b4b3e7b801c2105f6a508fd23dd137c9ee6e54fc31a94dfa`  
Extraction rule: only statements bearing on the score's meaning, possible inputs, thresholds, lookbacks, universe, data timing, or mandatory interpretation cautions. Line numbers refer to the supplied transcript. Quotes retain the transcript's Hinglish/Devanagari wording; translations do not add formula claims.

## Score mechanism and meaning

| Transcript quote | Faithful English translation | Classification |
|---|---|---|
| L29: “एक दिन में लगभग 100 ट्रेड्स होते हैं… एवरेज की बात मैं कर रहा हूं… एक एवरेज जनरेट होता है” | Imagine about 100 trades occur in a day; he is discussing an average generated from them. | Illustrative mechanism, not a disclosed formula. |
| L41: “100 ऑर्डर पर डे… एवरेज… पर ऑर्डर… 50 की क्वांटिटी… बड़ा इन्वेस्टर… बहुत बड़ा ट्रेड क्वांटिटी… सिस्टम… पकड़ लेता है” | Example: 100 orders per day with average quantity 50 per order; a large investor must use larger trade quantity, which the system catches. | Strongest stated candidate input: order/trade quantity relative to a usual per-order size. The numbers 100 and 50 are examples, not thresholds. |
| L43: “जिस स्टॉक में जितनी बड़ी एक्टिविटी होगी वहां पे नंबर उतने बड़े होते जाएंगे” | The larger the activity in a stock, the larger the displayed number becomes. | Monotonic score meaning. |
| L43–45: “अगर 2.8 है… एक्टिविटी बहुत स्लो… नॉर्मल” | A reading of 2.8 means slow/normal activity. | Example score interpretation, not a boundary. |
| L45: “3.5 के नीचे… नॉर्मल… 3.5 के ऊपर… एबनॉर्मल” | Below 3.5 is normal activity; above 3.5 is abnormal activity. | Explicit threshold. The transcript does not settle exactly-equal-to-3.5. |
| L197: “हाईएस्ट… मोर… एब्नॉर्मल एक्टिविटी… लोएस्ट… नो एब्नॉर्मल एक्टिविटी” | Higher numbers mean more abnormal activity; lower numbers mean no/lower abnormal activity. | Repeats monotonic meaning. |
| L165–167: “बाय भी हो सकता है, सेल भी… ऑर्डर ज्यादा पड़ेंगे तो ये नहीं पता… डाटा… एक्टिविटी बता रहा है… डायरेक्शन नहीं” | A high score can represent buying or selling, accumulation or distribution; order activity alone does not reveal side. The data shows activity, not direction. | Mandatory interpretation limitation. |
| L205: “डाटा किस हिसाब से बनाई है वो आपको मैं नहीं बता सकता बिकॉज़ दैट इज माय प्रोडक्ट” | He cannot disclose how the data is calculated because it is his product. | Explicitly confirms the formula is not stated. |

## Lookbacks and screening thresholds

| Transcript quote | Faithful English translation | Classification |
|---|---|---|
| L47–49: “लास्ट के… थ्री डेज… ग्रेटर देन 3.5… पहले लास्ट दिन पे फिर दो दिन और” | Filter the latest three days so each is greater than 3.5. | Explicit screening rule: three daily readings, each >3.5. This is a usage filter, not a score-computation lookback. |
| L47: “दो-तीन दिन और लगा लीजिए” | Add another two or three days if desired to narrow the list. | Optional extension to five or six daily readings. |
| L49: “लास्ट फोर डे… 3.5 पे एटलीस्ट थ्री… डाटा” | A last-four-day view is mentioned; the immediate example retains at least three days at 3.5/above. | The sentence is usage guidance and does not define a four-day score formula. |
| L55: “मैं कर देता हूं फोर… ग्रेटर देन फोर” | He raises the score filter to greater than 4 to reduce the list. | Optional screening threshold. |
| L107–109: “तीन दिन… एक्टिविटी कंटिन्यू… मल्टीपल डेज पे फोकस करो” | He discusses three days and says to focus on activity continuing across multiple days. | Persistence guidance, not a computation definition. |
| L127–129: “लास्ट फोर डेज का एवरेज… नंबर ग्रेटर देन फाइव” | Filter on the last four days' average and set it greater than 5. | Explicit aggregate screening rule: 4-day average >5. |
| L185: “एटलीस्ट… 3 टू सिक्स मंथ का टाइम चाहिए” | Users need at least 3–6 months to learn/use the data; one or two days is insufficient for market moves. | Adoption/observation horizon, not a score lookback. |

## Data quality, universe, and downstream inputs

| Transcript quote | Faithful English translation | Classification |
|---|---|---|
| L61–63 and L105: “स्टॉक स्प्लिट… डेटा को कंसीडर मत करिए… क्वांटिटी… चेंज” | Do not use readings around/after a stock split because share count and quantity change and mechanically inflate activity. | Explicit exclusion/quality rule. |
| L167: “वॉल्यूम प्रोफाइल… डायरेक्शन” | Use volume profile and the described chart rules to infer direction; the score does not provide it. | Downstream confirmation input, not a score input. |
| L177–179: “अपडेटिंग डेटा ऑन डेली बेसिस… अराउंड 9 PM… डेली… न्यू कॉलम” | The sheet is updated daily, around 9 PM in the example, by adding a new daily column. | Data frequency/timing. |
| L181: “लास्ट फाइव इयर्स, सिक्स इयर्स… बैक टेस्टिंग” | A professional plan can provide five or six years of history for backtesting. | Product history availability, not a formula lookback. |
| L187: “अराउंड 1600… 1600 टू 1700… लिक्विड स्टॉक… सेक्टर एंड इंडस्ट्री” | The sheet covers around 1,600–1,700 liquid stocks and includes sector and industry columns. | Stated universe/metadata. The supplied CSV has 1,627 named rows, which independently agrees. |
| L199: “बेस्ट इन द स्विंग ट्रेडिंग” | The presenter says the data is best used for swing trading. | Intended use horizon, not evidence of predictive validity. |

## What the transcript does **not** state

- No numerical rolling baseline for average order/trade size.
- No delivery quantity, delivery percentage, turnover, number-of-trades, ADR, sector-normalisation, cap, nonlinear exponent, or component weight in the score formula.
- No definition of whether “order,” “trade,” and executed transaction are technically identical in the vendor feed.
- No treatment of equality at 3.5, rounding order, missing sessions, corporate-action adjustment window, or universe-normalisation denominator.
