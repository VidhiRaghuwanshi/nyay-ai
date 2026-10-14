import { useCallback, useEffect, useState } from 'react';
import { Bell, CalendarDays, Loader2, RefreshCw, Scale } from 'lucide-react';
import { legaltechAPI } from '../services/api';

const TENANT_HEADERS = {
  'X-Organization-ID': 'org-demo',
  'X-User-ID': 'user-demo',
};

const initialListing = {
  matter_id: '',
  court: '',
  case_number: '',
  hearing_date: '',
  item_number: '',
  judge: '',
  status: 'scheduled',
};

export default function CourtDocket() {
  const [listing, setListing] = useState(initialListing);
  const [matterFilter, setMatterFilter] = useState('');
  const [listings, setListings] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [state, setState] = useState('');
  const [caseType, setCaseType] = useState('');
  const [syncResult, setSyncResult] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [listingResult, notificationResult] = await Promise.all([
        legaltechAPI.listCourtListings(matterFilter || undefined, TENANT_HEADERS),
        legaltechAPI.getCourtNotifications(true, TENANT_HEADERS),
      ]);
      setListings(Array.isArray(listingResult) ? listingResult : listingResult.listings || []);
      setNotifications(notificationResult.notifications || []);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Court docket data could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [matterFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const updateListing = (key, value) => {
    setListing((previous) => ({ ...previous, [key]: value }));
  };

  const createListing = async (event) => {
    event.preventDefault();
    if (!listing.matter_id || !listing.court || !listing.case_number || !listing.hearing_date) {
      setError('Matter ID, court, case number, and hearing date are required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await legaltechAPI.createCourtListing({
        ...listing,
        hearing_date: new Date(listing.hearing_date).toISOString(),
      }, TENANT_HEADERS);
      setListing(initialListing);
      setMessage('Court listing saved.');
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Court listing could not be saved.');
    } finally {
      setLoading(false);
    }
  };

  const syncNdap = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await legaltechAPI.syncNdapBacklog(
        { state: state || undefined, case_type: caseType || undefined },
        TENANT_HEADERS,
      );
      setSyncResult(result);
      setMessage(`NDAP sync completed: ${result.matched_rows} matching rows.`);
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NDAP synchronization failed.');
    } finally {
      setLoading(false);
    }
  };

  const markNotificationRead = async (notificationId) => {
    setError('');
    try {
      await legaltechAPI.markCourtNotificationRead(notificationId, TENANT_HEADERS);
      setNotifications((previous) => previous.filter((item) => item.id !== notificationId));
      setMessage('Notification marked as read.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Notification could not be marked as read.');
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <div className="section-kicker"><Scale size={14} /> Court docket tracker</div>
          <h1 className="page-title">Hearings and court updates</h1>
          <p className="page-subtitle">Track matter listings and synchronize public High Court backlog data.</p>
        </div>
        <button className="btn-secondary" type="button" onClick={loadData} disabled={loading}>
          {loading ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />}
          Refresh
        </button>
      </div>

      {message && <p className="upload-status">{message}</p>}
      {error && <p className="error-message">{error}</p>}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 20 }}>
        <section className="panel">
          <div className="panel-title">Add hearing listing</div>
          <form onSubmit={createListing}>
            <label className="field-label" htmlFor="docket-matter">Matter ID</label>
            <input id="docket-matter" className="input-ink" value={listing.matter_id} onChange={(event) => updateListing('matter_id', event.target.value)} />
            <label className="field-label" htmlFor="docket-court">Court</label>
            <input id="docket-court" className="input-ink" value={listing.court} onChange={(event) => updateListing('court', event.target.value)} placeholder="e.g. Delhi High Court" />
            <label className="field-label" htmlFor="docket-case">Case number</label>
            <input id="docket-case" className="input-ink" value={listing.case_number} onChange={(event) => updateListing('case_number', event.target.value)} />
            <label className="field-label" htmlFor="docket-date">Hearing date</label>
            <input id="docket-date" className="input-ink" type="datetime-local" value={listing.hearing_date} onChange={(event) => updateListing('hearing_date', event.target.value)} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div>
                <label className="field-label" htmlFor="docket-item">Item number</label>
                <input id="docket-item" className="input-ink" value={listing.item_number} onChange={(event) => updateListing('item_number', event.target.value)} />
              </div>
              <div>
                <label className="field-label" htmlFor="docket-judge">Judge</label>
                <input id="docket-judge" className="input-ink" value={listing.judge} onChange={(event) => updateListing('judge', event.target.value)} />
              </div>
            </div>
            <button className="btn-primary" type="submit" disabled={loading}>
              <CalendarDays size={16} /> Save listing
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-title">Public backlog synchronization</div>
          <p className="panel-muted">Synchronize the supplied NDAP High Court dataset and create notifications when tracked values change.</p>
          <label className="field-label" htmlFor="ndap-state">State filter</label>
          <input id="ndap-state" className="input-ink" value={state} onChange={(event) => setState(event.target.value)} placeholder="Optional" />
          <label className="field-label" htmlFor="ndap-type">Case type filter</label>
          <input id="ndap-type" className="input-ink" value={caseType} onChange={(event) => setCaseType(event.target.value)} placeholder="Optional" />
          <button className="btn-secondary" type="button" onClick={syncNdap} disabled={loading}>
            {loading ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />}
            Sync NDAP data
          </button>
          {syncResult && (
            <div className="panel-muted" style={{ marginTop: 16 }}>
              Inserted {syncResult.inserted}; updated {syncResult.updated}; notifications {syncResult.notifications_created}.
            </div>
          )}
        </section>
      </div>

      <section className="panel" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
          <div className="panel-title">Upcoming listings</div>
          <input className="input-ink" style={{ maxWidth: 260 }} value={matterFilter} onChange={(event) => setMatterFilter(event.target.value)} placeholder="Filter by matter ID" />
        </div>
        {!listings.length ? <div className="panel-empty">No manual court listings found.</div> : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead><tr><th>Matter</th><th>Court</th><th>Case number</th><th>Hearing</th><th>Item</th><th>Status</th></tr></thead>
              <tbody>{listings.map((item) => (
                <tr key={item.id || item._id}>
                  <td>{item.matter_id}</td><td>{item.court}</td><td>{item.case_number}</td>
                  <td>{new Date(item.hearing_date).toLocaleString()}</td><td>{item.item_number || '—'}</td><td>{item.status}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel" style={{ marginTop: 20 }}>
        <div className="panel-title"><Bell size={15} /> Unread docket notifications</div>
        {!notifications.length ? <div className="panel-empty">No unread court updates.</div> : notifications.map((item) => (
          <div key={item.id || item._id} className="risk-item">
            <div className="risk-badge medium">Update</div>
            <div style={{ flex: 1 }}><strong>{item.message}</strong><p>{new Date(item.created_at).toLocaleString()}</p></div>
            <button className="btn-secondary" type="button" onClick={() => markNotificationRead(item.id || item._id)}>
              Mark read
            </button>
          </div>
        ))}
      </section>
    </div>
  );
}
