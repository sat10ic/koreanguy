import SymbolChip from "./SymbolChip.jsx";

/**
 * SymbolCard — expanded block form of the SymbolChip fusion (design §0.2B).
 * Used on Setups + Watchlist cards (built against stubs in this pass — see
 * App.jsx SetupsPage/WatchlistPage). Same three source-bands as SymbolChip,
 * plus a left-rail band color for the card's headline verdict, and a slot
 * for per-screen metric children.
 */
export default function SymbolCard({
  symbol,
  rs = null,
  rsAsOf = null,
  deliveryPct = null,
  deliveryAsOf = null,
  changePct = null,
  fyersConnected = false,
  verdictBand = "muted",
  onSelect,
  children,
}) {
  const railCls = {
    bull: "bg-bull",
    warn: "bg-warn",
    bear: "bg-bear",
    muted: "bg-muted",
  }[verdictBand] || "bg-muted";

  return (
    <div
      data-testid={`symbol-card-${symbol}`}
      className="relative overflow-hidden border border-hairline bg-card p-3 pl-4"
    >
      <div className={"absolute left-0 top-0 h-full w-[3px] " + railCls} />
      <div className="mb-2">
        <SymbolChip
          symbol={symbol}
          rs={rs}
          rsAsOf={rsAsOf}
          deliveryPct={deliveryPct}
          deliveryAsOf={deliveryAsOf}
          changePct={changePct}
          fyersConnected={fyersConnected}
          onSelect={onSelect}
        />
      </div>
      {children}
    </div>
  );
}
