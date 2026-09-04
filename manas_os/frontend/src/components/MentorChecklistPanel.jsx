import { useEffect, useState } from "react";
import { getMentorChecklistResponses, getMentorChecklists, postMentorChecklistResponse } from "../api.js";

const today = () => new Date().toISOString().slice(0, 10);

export default function MentorChecklistPanel() {
  const [state, setState] = useState({ loading: true, error: null, checklists: [] });
  const [responses, setResponses] = useState({});
  const [saving, setSaving] = useState({});
  const date = today();

  useEffect(() => {
    let alive = true;
    getMentorChecklists()
      .then(async (payload) => {
        const checklists = payload.checklists || [];
        const responseRows = await Promise.all(
          checklists.map((checklist) => getMentorChecklistResponses(checklist.id, date))
        );
        if (!alive) return;
        const next = {};
        responseRows.forEach((row, index) => {
          next[checklists[index].id] = row.responses || {};
        });
        setResponses(next);
        setState({ loading: false, error: null, checklists });
      })
      .catch((error) => {
        if (alive) setState({ loading: false, error: error.message, checklists: [] });
      });
    return () => {
      alive = false;
    };
  }, [date]);

  const toggle = async (checklistId, itemId, checked) => {
    setResponses((prev) => ({
      ...prev,
      [checklistId]: { ...(prev[checklistId] || {}), [itemId]: checked },
    }));
    setSaving((prev) => ({ ...prev, [`${checklistId}:${itemId}`]: true }));
    try {
      await postMentorChecklistResponse(checklistId, { date, item_id: itemId, checked });
    } catch (error) {
      setResponses((prev) => ({
        ...prev,
        [checklistId]: { ...(prev[checklistId] || {}), [itemId]: !checked },
      }));
      setState((prev) => ({ ...prev, error: error.message }));
    } finally {
      setSaving((prev) => ({ ...prev, [`${checklistId}:${itemId}`]: false }));
    }
  };

  if (state.loading) {
    return <section className="border border-hairline bg-card p-3 font-mono text-[11px] text-ink3">loading mentor checklist...</section>;
  }

  if (state.error && state.checklists.length === 0) {
    return <section className="border border-hairline bg-card p-3 font-mono text-[11px] text-bear">{state.error}</section>;
  }

  return (
    <div className="space-y-3">
      {state.error && <div className="font-mono text-[11px] text-bear">{state.error}</div>}
      {state.checklists.map((checklist) => (
        <section key={checklist.id} className="border border-hairline bg-card p-3">
          <div className="mb-1 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
            Mentor checklist - {checklist.mentor}
          </div>
          <div className="mb-3 font-sans text-[12px] text-ink3">{checklist.title}</div>
          <ul className="space-y-2">
            {(checklist.items || []).map((item) => {
              const key = `${checklist.id}:${item.id}`;
              const checked = Boolean(responses[checklist.id]?.[item.id]);
              return (
                <li key={item.id} className="border border-hairline2 bg-raised px-2 py-2">
                  <label className="flex items-start gap-2 font-sans text-[13px] text-ink2">
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={Boolean(saving[key])}
                      onChange={(event) => toggle(checklist.id, item.id, event.target.checked)}
                      className="mt-0.5"
                    />
                    <span>{item.text}</span>
                  </label>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
