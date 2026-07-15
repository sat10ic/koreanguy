import React, { useState, useEffect } from "react";
import { fetchTraderProfile, updateTraderProfile } from "./api.js";
import "./TraderProfileModal.css";

export default function TraderProfileModal({ onProfileConfirmed }) {
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [capital, setCapital] = useState("");
  const [mode, setMode] = useState("LEARNING");
  const [paperMode, setPaperMode] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTraderProfile()
      .then((data) => {
        setProfile(data);
        if (data.account_capital) setCapital(String(data.account_capital));
        if (data.experience_mode) setMode(data.experience_mode);
        setPaperMode(data.paper_mode !== 0 && data.paper_mode !== false);
        setLoading(false);
      })
      .catch((err) => {
        setError(String(err));
        setLoading(false);
      });
  }, []);

  const requiresConfirmation = () => {
    if (!profile) return false;
    return !profile.profile_confirmed_at || profile.account_capital <= 0;
  };

  if (loading) return null;
  if (!requiresConfirmation()) return null;

  const handleSave = (e) => {
    e.preventDefault();
    const cap = parseFloat(capital);
    if (isNaN(cap) || cap <= 0) {
      setError("Capital must be greater than 0");
      return;
    }
    const payload = {
      account_capital: cap,
      experience_mode: mode,
      paper_mode: paperMode
    };
    updateTraderProfile(payload)
      .then((data) => {
        setProfile(data);
        onProfileConfirmed && onProfileConfirmed(data);
      })
      .catch((err) => setError(String(err)));
  };

  return (
    <div className="trader-profile-modal-overlay">
      <div className="trader-profile-modal">
        <h2>Complete Trader Profile</h2>
        <p>Before you can size positions, you must confirm your capital and experience mode.</p>
        {error && <div className="trader-profile-error">{error}</div>}
        <form onSubmit={handleSave}>
          <div className="form-group">
            <label>Account Capital (Rs)</label>
            <input 
              type="number" 
              value={capital} 
              onChange={(e) => setCapital(e.target.value)} 
              placeholder="e.g. 1000000"
              required
            />
          </div>
          <div className="form-group">
            <label>Experience Mode</label>
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="LEARNING">LEARNING (max 0.20% risk, max 4 positions)</option>
              <option value="STANDARD">STANDARD (requires expert confirmation)</option>
              <option value="AGGRESSIVE">AGGRESSIVE (requires expert confirmation)</option>
            </select>
          </div>
          <button type="submit" className="save-btn">Confirm Profile</button>
        </form>
      </div>
    </div>
  );
}
