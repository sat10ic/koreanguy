import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from traderlog.llm.classify import validate_classification

input_path = r"c:\Users\satta\Downloads\koreanguy\traderlog\_class_tranches\class_tranche_030_input.json"
output_path = r"c:\Users\satta\Downloads\koreanguy\traderlog\_class_tranches\class_tranche_030_output.json"

with open(input_path, "r", encoding="utf-8") as f:
    input_data = json.load(f)

posts_by_id = {p["post_id"]: p["text"] for p in input_data["posts"]}

classifications = [
    {
        "post_id": "2066157000418005135",
        "payload": {
            "kind": "education",
            "confidence": 0.95,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Teachable principle regarding technical analysis chart line preferences."
        }
    },
    {
        "post_id": "2066169549389746460",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Promotional update announcing newsletter upload."
        }
    },
    {
        "post_id": "2066330917946495341",
        "payload": {
            "kind": "breadth",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Macro news commentary regarding US-Iran deal and overall market sentiment."
        }
    },
    {
        "post_id": "2066352867775308067",
        "payload": {
            "kind": "watch_idea",
            "confidence": 0.9,
            "symbols": ["SOTL"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Posting SOTL ticker hashtag as a watch idea."
        }
    },
    {
        "post_id": "2066370702006255801",
        "payload": {
            "kind": "noise",
            "confidence": 0.85,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Casual commentary describing Data Pattern as a nerd stock."
        }
    },
    {
        "post_id": "2066370916582596921",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Casual commentary in Hindi reacting to news."
        }
    },
    {
        "post_id": "2066374284768083978",
        "payload": {
            "kind": "education",
            "confidence": 0.85,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Educational commentary advising risk management and trailing stops."
        }
    },
    {
        "post_id": "2066399785096265769",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.98,
            "symbols": ["AEQUS"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Announces new long position entry in AEQUS with stop loss."
        }
    },
    {
        "post_id": "2066401731861451255",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.95,
            "symbols": ["AEQUS"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Trade progress update on open AEQUS position reaching 195+."
        }
    },
    {
        "post_id": "2066404620453429667",
        "payload": {
            "kind": "noise",
            "confidence": 0.99,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Off-topic personal social media commentary."
        }
    },
    {
        "post_id": "2066405496039584050",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.95,
            "symbols": ["AEQUS"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Trade progress update on AEQUS reaching 200 with trade management commentary."
        }
    },
    {
        "post_id": "2066405788701401416",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Reply to another user speculating on trade execution."
        }
    },
    {
        "post_id": "2066405991382712321",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Reply in thread questioning trade sizing speculation."
        }
    },
    {
        "post_id": "2066406149210210466",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "User reply guessing trade actions."
        }
    },
    {
        "post_id": "2066406286284251547",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Follow-up reply in interactive thread."
        }
    },
    {
        "post_id": "2066406337068793996",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Follower question asking about stock screener."
        }
    },
    {
        "post_id": "2066406425690280401",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Follower reply guessing trade execution."
        }
    },
    {
        "post_id": "2066406429293203752",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Reply recommending educational video episode."
        }
    },
    {
        "post_id": "2066406473266270271",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Short interactive question in thread."
        }
    },
    {
        "post_id": "2066407318632403390",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.98,
            "symbols": ["AEQUS"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Reports partial exit at 202 and moving stop loss to breakeven on AEQUS."
        }
    },
    {
        "post_id": "2066407764671471707",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Follower question asking about generic trade management approach."
        }
    },
    {
        "post_id": "2066407781872304289",
        "payload": {
            "kind": "theme",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Discussing company strategy and base structure for Angel One."
        }
    },
    {
        "post_id": "2066408248157360475",
        "payload": {
            "kind": "noise",
            "confidence": 0.95,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Short reply answering a follower question."
        }
    },
    {
        "post_id": "2066409483564437968",
        "payload": {
            "kind": "noise",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Question regarding trade classification mechanics."
        }
    },
    {
        "post_id": "2066410139129913742",
        "payload": {
            "kind": "noise",
            "confidence": 0.98,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Single-word response in thread."
        }
    },
    {
        "post_id": "2066410347352006694",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.98,
            "symbols": ["AEQUS"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Reports partial exit at 202 and moving stop loss to breakeven on AEQUS."
        }
    },
    {
        "post_id": "2066431657729765857",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.95,
            "symbols": ["AEQUS"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Trade status update holding AEQUS as price reaches 210+."
        }
    },
    {
        "post_id": "2066437905757983033",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.98,
            "symbols": ["EXICOM"],
            "play_type": "unclear",
            "conviction_words": ["half size"],
            "reason": "Announces intraday entry in EXICOM with half size and defined risk."
        }
    },
    {
        "post_id": "2066442991208972670",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.98,
            "symbols": [],
            "play_type": "momentum_burst",
            "conviction_words": [],
            "reason": "Reports full exit of position at 160 taking 4R profit on a momentum burst trade."
        }
    },
    {
        "post_id": "2066444242843799553",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.98,
            "symbols": ["ELECON"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Announces new long position entry in ELECON with stop loss."
        }
    },
    {
        "post_id": "2066501488860635539",
        "payload": {
            "kind": "watch_idea",
            "confidence": 0.95,
            "symbols": ["FRO"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Highlights FRO as a high-quality watchlist idea based on price structure."
        }
    },
    {
        "post_id": "2066517278796234849",
        "payload": {
            "kind": "breadth",
            "confidence": 0.95,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Market breadth commentary advising risk management and capital preservation."
        }
    },
    {
        "post_id": "2066530094190055551",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.95,
            "symbols": ["CRUDE"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Reports flag short trade in Crude with risk-free stop at cost."
        }
    },
    {
        "post_id": "2066530675742945301",
        "payload": {
            "kind": "breadth",
            "confidence": 0.9,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Market breadth commentary regarding lack of actionable setups."
        }
    },
    {
        "post_id": "2066532862091022571",
        "payload": {
            "kind": "breadth",
            "confidence": 0.95,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Macro market commentary reflecting on historical market correction narrative."
        }
    },
    {
        "post_id": "2066533059000983629",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.95,
            "symbols": ["AEROFLEX", "CMR"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Reports position updates including additions in Aeroflex, Bharat Forge, Angel One, and stopped out trade in CMR Green."
        }
    },
    {
        "post_id": "2066533818950164756",
        "payload": {
            "kind": "education",
            "confidence": 0.85,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Brief educational tip advising proper position sizing."
        }
    },
    {
        "post_id": "2066535254912012689",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.95,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Reports position exit at cost after moving 2R."
        }
    },
    {
        "post_id": "2066736992294236382",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.95,
            "symbols": ["QUADFUTURE"],
            "play_type": "breakout",
            "conviction_words": [],
            "reason": "Reports flag play trade execution in quadfuture booking 4R return."
        }
    },
    {
        "post_id": "2066737414727700869",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.98,
            "symbols": ["PREMEXPLN"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Announces trade entry in PREMEXPLN with entry level 698 and stop 680."
        }
    },
    {
        "post_id": "2066737438236786773",
        "payload": {
            "kind": "watch_idea",
            "confidence": 0.98,
            "symbols": ["INOXINDIA"],
            "play_type": "breakout",
            "conviction_words": [],
            "reason": "Highlights INOXINDIA as a watchlist setup forming a breakout and consolidation structure."
        }
    },
    {
        "post_id": "2066763045779706248",
        "payload": {
            "kind": "education",
            "confidence": 0.98,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Shares educational backtest insights regarding momentum trade setups."
        }
    },
    {
        "post_id": "2066763049693073455",
        "payload": {
            "kind": "education",
            "confidence": 0.98,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": ["LARGE size"],
            "reason": "Outlines educational framework and sizing strategy for expansion day entries."
        }
    },
    {
        "post_id": "2066776440792875230",
        "payload": {
            "kind": "trade_event",
            "confidence": 0.98,
            "symbols": ["SUVEN"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Announces new long position entry in SUVEN with entry level and stop loss."
        }
    },
    {
        "post_id": "2066780267516395958",
        "payload": {
            "kind": "noise",
            "confidence": 0.95,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Social media banter regarding trade criticism."
        }
    },
    {
        "post_id": "2066782442275627495",
        "payload": {
            "kind": "breadth",
            "confidence": 0.95,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Market breadth commentary warning of lack of follow-through and emphasizing capital protection."
        }
    },
    {
        "post_id": "2066783765977043019",
        "payload": {
            "kind": "watch_idea",
            "confidence": 0.95,
            "symbols": ["INOX"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Highlights Inox India consolidating in a flag pattern after a 20% burst."
        }
    },
    {
        "post_id": "2066786076338118692",
        "payload": {
            "kind": "breadth",
            "confidence": 0.95,
            "symbols": [],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Market commentary highlighting risk management and staying light in volatile market."
        }
    },
    {
        "post_id": "2066806464367473134",
        "payload": {
            "kind": "watch_idea",
            "confidence": 0.95,
            "symbols": ["RAIN"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Technical analysis and watchlist plan for RAIN Industries."
        }
    },
    {
        "post_id": "2066849967021719801",
        "payload": {
            "kind": "watch_idea",
            "confidence": 0.9,
            "symbols": ["NETWEB"],
            "play_type": "unclear",
            "conviction_words": [],
            "reason": "Mentions Netweb channel pattern breakdown as a technical observation."
        }
    }
]

# Validate each classification against contract
validated_results = []
for item in classifications:
    pid = item["post_id"]
    stext = posts_by_id[pid]
    try:
        c = validate_classification(item["payload"], stext)
    except Exception as e:
        print(f"Validation failed for post_id {pid}: {e}")
        raise e
    validated_results.append(item)

output_data = {
    "tranche_id": input_data["tranche_id"],
    "results": validated_results
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)

print(f"Successfully validated all {len(validated_results)} posts and wrote output to {output_path}")
