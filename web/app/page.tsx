"use client";

import React, { useEffect, useMemo, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Lead = {
  id: string;
  company: string;
  contact_name: string;
  email: string;
  title?: string;
  status: string;
  created_at: string;
  website?: string | null;
  industry?: string | null;
  employee_count?: string | null;
  location?: string | null;
  source?: string | null;
  icp_score?: string | null;
  qualification_reason?: string | null;
  qualified?: string | null;
  research_summary?: string | null;
  pain_points?: string | null;
  personalization_note?: string | null;
};

type Draft = {
  id: string;
  lead_id: string;
  company: string;
  contact_name: string;
  email: string;
  subject: string;
  body: string;
  status: string;
  delivery_status: string;
  delivery_error?: string | null;
  message_id?: string | null;
  created_at: string;
  approved_at?: string | null;
  sent_at?: string | null;
};

type Activity = {
  id: string;
  message: string;
  created_at: string;
};

type Agent = {
  id: string;
  name: string;
  role: string;
  description?: string | null;
  status: string;
  connected_tools?: string | null;
  created_at: string;
};

type AgentStats = {
  agent_id: string;
  name: string;
  role: string;
  tasks: number;
  revenue_impact: number;
  hours_saved: number;
  errors: number;
};

type GovernanceEvent = {
  id: string;
  agent_id: string;
  event_type: string;
  task_name?: string | null;
  status?: string | null;
  error_message?: string | null;
  details?: string | null;
  created_at: string;
};

type RoiSummary = {
  total_hours_saved: number;
  total_revenue_impact: number;
  sales_emails_sent: number;
};

type Stats = {
  total_leads: number;
  new_leads: number;
  drafts_pending: number;
  drafts_approved: number;
  drafts_sent: number;
};

type TabKey =
  | "dashboard"
  | "leads"
  | "drafts"
  | "activity"
  | "agents"
  | "monitoring"
  | "governance"
  | "roi";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    new: "bg-blue-100 text-blue-700 border-blue-200",
    researched: "bg-purple-100 text-purple-700 border-purple-200",
    draft_created: "bg-yellow-100 text-yellow-700 border-yellow-200",
    pending: "bg-yellow-100 text-yellow-700 border-yellow-200",
    approved: "bg-green-100 text-green-700 border-green-200",
    sent: "bg-slate-200 text-slate-700 border-slate-300",
    replied: "bg-pink-100 text-pink-700 border-pink-200",
  };

  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wide ${
        styles[status] || "bg-slate-100 text-slate-700 border-slate-200"
      }`}
    >
      {status.replace("_", " ")}
    </span>
  );
}

function DeliveryBadge({
  status,
}: {
  status: "queued" | "sent" | "failed" | string;
}) {
  const styles: Record<string, string> = {
    queued: "bg-yellow-100 text-yellow-700 border-yellow-200",
    sent: "bg-green-100 text-green-700 border-green-200",
    failed: "bg-red-100 text-red-700 border-red-200",
  };

  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wide ${
        styles[status] || "bg-slate-100 text-slate-700 border-slate-200"
      }`}
    >
      {status}
    </span>
  );
}

function StatCard({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-sm font-medium text-slate-500">{label}</div>
      <div className="mt-2 text-3xl font-black text-slate-900">{value}</div>
    </div>
  );
}

export default function SentinelPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("dashboard");
  const [loading, setLoading] = useState(false);

  const [leads, setLeads] = useState<Lead[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentStats, setAgentStats] = useState<AgentStats[]>([]);
  const [governanceEvents, setGovernanceEvents] = useState<GovernanceEvent[]>(
    []
  );
  const [roiSummary, setRoiSummary] = useState<RoiSummary | null>(null);
  const [stats, setStats] = useState<Stats>({
    total_leads: 0,
    new_leads: 0,
    drafts_pending: 0,
    drafts_approved: 0,
    drafts_sent: 0,
  });

  const [helperOutput, setHelperOutput] = useState(
    "Sentinel AI is connected to your FastAPI backend."
  );

  const [editingDraftId, setEditingDraftId] = useState<string | null>(null);
  const [draftSubject, setDraftSubject] = useState("");
  const [draftBody, setDraftBody] = useState("");

  async function loadAll() {
    try {
      const [
        leadsRes,
        draftsRes,
        activityRes,
        statsRes,
        agentsRes,
        agentStatsRes,
        govRes,
        roiRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/leads`),
        fetch(`${API_BASE}/drafts`),
        fetch(`${API_BASE}/activity`),
        fetch(`${API_BASE}/stats`),
        fetch(`${API_BASE}/agents`),
        fetch(`${API_BASE}/agent_stats`),
        fetch(`${API_BASE}/governance_events`),
        fetch(`${API_BASE}/roi_summary`),
      ]);

      const [
        leadsData,
        draftsData,
        activityData,
        statsData,
        agentsData,
        agentStatsData,
        govData,
        roiData,
      ] = await Promise.all([
        leadsRes.json(),
        draftsRes.json(),
        activityRes.json(),
        statsRes.json(),
        agentsRes.json(),
        agentStatsRes.json(),
        govRes.json(),
        roiRes.json(),
      ]);

      setLeads(leadsData);
      setDrafts(draftsData);
      setActivity(activityData);
      setStats(statsData);
      setAgents(agentsData);
      setAgentStats(agentStatsData);
      setGovernanceEvents(govData);
      setRoiSummary(roiData);
    } catch (error) {
      console.error(error);
      setHelperOutput(
        "Could not connect to backend. Make sure FastAPI is running on localhost:8000."
      );
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleGenerateLeads() {
    setLoading(true);
    try {
      // For now, seed with sample leads via the real import endpoint.
      const res = await fetch(`${API_BASE}/import_real_leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          leads: [
            {
              company: "Acme Logistics",
              contact_name: "Sarah Chen",
              email: "sarah@acmelogistics.com",
              title: "Operations Manager",
              industry: "Logistics",
              employee_count: "11-50",
              location: "Austin, TX",
              source: "sample",
            },
            {
              company: "NorthPeak Dental",
              contact_name: "David Kim",
              email: "david@northpeakdental.com",
              title: "Practice Owner",
              industry: "Dental",
              employee_count: "1-10",
              location: "Denver, CO",
              source: "sample",
            },
            {
              company: "BlueRiver CPA Group",
              contact_name: "Emily Patel",
              email: "emily@bluerivercpa.com",
              title: "Managing Partner",
              industry: "CPA",
              employee_count: "11-50",
              location: "Chicago, IL",
              source: "sample",
            },
          ],
        }),
      });
      const data = await res.json();
      setHelperOutput(`Imported ${data.length} real leads (sample set).`);
      await loadAll();
      setActiveTab("leads");
    } catch (error) {
      console.error(error);
      setHelperOutput("Failed to generate leads.");
    } finally {
      setLoading(false);
    }
  }

  async function handleQualifyLeads() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/qualify_leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok) {
        setHelperOutput(data.detail || "Failed to qualify leads.");
        return;
      }
      setHelperOutput("Leads qualified with ICP scores.");
      setLeads(data);
      setActiveTab("leads");
    } catch (error) {
      console.error(error);
      setHelperOutput("Failed to qualify leads.");
    } finally {
      setLoading(false);
    }
  }

  function parseCsv(text: string): Lead[] {
    const lines = text
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length < 2) return [];

    const rawHeader = lines[0].split(",").map((h) => h.trim());
    const normalizedHeader = rawHeader.map((h) =>
      h
        .replace(/["']/g, "")
        .trim()
        .toLowerCase()
        .replace(/[\s_-]+/g, "")
    );

    const findIdx = (candidates: string[]): number => {
      for (let i = 0; i < normalizedHeader.length; i += 1) {
        if (candidates.includes(normalizedHeader[i])) return i;
      }
      return -1;
    };

    const companyIdx = findIdx([
      "company",
      "companyname",
      "business",
      "businessname",
      "account",
      "accountname",
    ]);
    const contactIdx = findIdx([
      "contactname",
      "name",
      "fullname",
      "full_name",
      "person",
      "contact",
    ]);
    const emailIdx = findIdx(["email", "emailaddress", "workemail"]);

    if (companyIdx === -1 || contactIdx === -1 || emailIdx === -1) {
      return [];
    }

    const titleIdx = findIdx(["title", "jobtitle", "role", "position"]);
    const websiteIdx = findIdx(["website", "domain", "url"]);
    const industryIdx = findIdx(["industry", "vertical"]);
    const employeeIdx = findIdx(["employeecount", "headcount", "employees", "size"]);
    const locationIdx = findIdx(["location", "city", "region"]);
    const sourceIdx = findIdx(["source", "list", "segment"]);

    return lines.slice(1).map((line) => {
      const cells = line.split(",").map((c) => c.trim());
      const get = (idx: number) => (idx >= 0 ? cells[idx] || "" : "");

      return {
        id: "",
        company: get(companyIdx),
        contact_name: get(contactIdx),
        email: get(emailIdx),
        title: get(titleIdx),
        status: "new",
        created_at: new Date().toISOString(),
        website: get(websiteIdx),
        industry: get(industryIdx),
        employee_count: get(employeeIdx),
        location: get(locationIdx),
        source: get(sourceIdx) || "csv",
        icp_score: null,
        qualification_reason: null,
        qualified: null,
      };
    });
  }

  async function handleCsvUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setHelperOutput("Importing leads from CSV...");

    try {
      const text = await file.text();
      const parsed = parseCsv(text).filter(
        (l) => l.company && l.contact_name && l.email
      );

      if (parsed.length === 0) {
        setHelperOutput("CSV parsed, but no valid leads were found.");
        return;
      }

      const res = await fetch(`${API_BASE}/import_real_leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          leads: parsed.map(
            ({
              company,
              contact_name,
              email,
              title,
              website,
              industry,
              employee_count,
              location,
              source,
            }) => ({
              company,
              contact_name,
              email,
              title,
              website,
              industry,
              employee_count,
              location,
              source,
            })
          ),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setHelperOutput(data.detail || "Failed to import CSV leads.");
        return;
      }

      setHelperOutput(
        `Imported ${data.length} leads from CSV. Click "Qualify Leads" next.`
      );
      await loadAll();
      setActiveTab("leads");
    } catch (err) {
      console.error(err);
      setHelperOutput("Failed to import CSV leads.");
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  }

  async function handleCreateDraft(leadId: string) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/create_draft/${leadId}`, {
        method: "POST",
      });

      const data = await res.json();

      if (!res.ok) {
        setHelperOutput(data.detail || "Failed to create draft.");
        return;
      }

      setHelperOutput(`Draft created for ${data.company}.`);
      await loadAll();
      setActiveTab("drafts");
    } catch (error) {
      console.error(error);
      setHelperOutput("Failed to create draft.");
    } finally {
      setLoading(false);
    }
  }

  async function handleApproveDraft(draftId: string) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/approve_draft/${draftId}`, {
        method: "POST",
      });

      const data = await res.json();

      if (!res.ok) {
        setHelperOutput(data.detail || "Failed to approve draft.");
        return;
      }

      setHelperOutput(`Draft approved for ${data.company}.`);
      await loadAll();
    } catch (error) {
      console.error(error);
      setHelperOutput("Failed to approve draft.");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartEditDraft(draft: Draft) {
    setEditingDraftId(draft.id);
    setDraftSubject(draft.subject);
    setDraftBody(draft.body);
    setHelperOutput("Editing draft. Update subject/body, then Save.");
  }

  async function handleSaveDraftEdits() {
    if (!editingDraftId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/drafts/${editingDraftId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: draftSubject, body: draftBody }),
      });
      const data = await res.json();
      if (!res.ok) {
        setHelperOutput(data.detail || "Failed to save draft edits.");
        return;
      }
      setHelperOutput("Draft saved.");
      setEditingDraftId(null);
      await loadAll();
    } catch (error) {
      console.error(error);
      setHelperOutput("Failed to save draft edits.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSendDraft(draftId: string) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/send_draft/${draftId}`, {
        method: "POST",
      });

      const data = await res.json();

      if (!res.ok) {
        setHelperOutput(data.detail || "Failed to send draft.");
        return;
      }

      setHelperOutput(`Draft sent to ${data.email}.`);
      await loadAll();
    } catch (error) {
      console.error(error);
      setHelperOutput("Failed to send draft.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResearchLead(leadId: string) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/research_lead/${leadId}`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) {
        setHelperOutput(data.detail || "Failed to research lead.");
        return;
      }
      setHelperOutput(`Researched ${data.company}.`);
      await loadAll();
    } catch (error) {
      console.error(error);
      setHelperOutput("Failed to research lead.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateResearchedDraft(leadId: string) {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/generate_researched_draft/${leadId}`,
        {
          method: "POST",
        }
      );
      const data = await res.json();
      if (!res.ok) {
        setHelperOutput(data.detail || "Failed to generate researched draft.");
        return;
      }
      setHelperOutput(`Generated researched draft for ${data.company}.`);
      await loadAll();
      setActiveTab("drafts");
    } catch (error) {
      console.error(error);
      setHelperOutput("Failed to generate researched draft.");
    } finally {
      setLoading(false);
    }
  }

  const draftsByLead = useMemo(() => {
    const map: Record<string, Draft[]> = {};
    for (const draft of drafts) {
      if (!map[draft.lead_id]) map[draft.lead_id] = [];
      map[draft.lead_id].push(draft);
    }
    return map;
  }, [drafts]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-sm font-bold uppercase tracking-[0.2em] text-sky-600">
              Sentinel AI
            </div>
            <h1 className="mt-2 text-4xl font-black tracking-tight">
              AI Outreach Workflow Control Center
            </h1>
            <p className="mt-3 max-w-3xl text-base text-slate-600">
              Manage lead generation, draft creation, approval workflow, send
              actions, and activity logs from one place.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleGenerateLeads}
              className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:opacity-90 disabled:opacity-50"
              disabled={loading}
            >
              {loading ? "Working..." : "Generate Leads"}
            </button>

            <button
              onClick={handleQualifyLeads}
              className="rounded-2xl border border-sky-300 bg-white px-5 py-3 text-sm font-bold text-sky-700 shadow-sm transition hover:bg-sky-50 disabled:opacity-50"
              disabled={loading || leads.length === 0}
            >
              Qualify Leads
            </button>

            <label className="inline-flex cursor-pointer items-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-900 shadow-sm transition hover:bg-slate-100">
              <span>Import CSV</span>
              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={handleCsvUpload}
              />
            </label>

            <button
              onClick={loadAll}
              className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-900 shadow-sm transition hover:bg-slate-100"
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="mt-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-sm font-semibold text-slate-500">
            AI Helper
          </div>
          <div className="mt-2 text-base text-slate-800">{helperOutput}</div>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-5">
          <StatCard label="Total Leads" value={stats.total_leads} />
          <StatCard label="New Leads" value={stats.new_leads} />
          <StatCard label="Drafts Pending" value={stats.drafts_pending} />
          <StatCard label="Drafts Approved" value={stats.drafts_approved} />
          <StatCard label="Drafts Sent" value={stats.drafts_sent} />
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          {[
            ["dashboard", "Dashboard"],
            ["leads", "Leads"],
            ["drafts", "Drafts"],
            ["activity", "Activity"],
            ["agents", "Agents"],
            ["monitoring", "Monitoring"],
            ["governance", "Governance"],
            ["roi", "ROI"],
          ].map(([key, label]) => {
            const selected = activeTab === key;
            return (
              <button
                key={key}
                onClick={() => setActiveTab(key as TabKey)}
                className={`rounded-2xl px-4 py-2 text-sm font-bold transition ${
                  selected
                    ? "bg-slate-900 text-white"
                    : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>

        {activeTab === "dashboard" && (
          <section className="mt-8 grid gap-6 lg:grid-cols-2">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-black">Workflow Summary</h2>
              <div className="mt-4 space-y-3 text-sm text-slate-700">
                <div>1. Generate leads</div>
                <div>2. Create draft for each lead</div>
                <div>3. Approve draft</div>
                <div>4. Send draft</div>
                <div>5. Track status and activity</div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-black">Recent Activity</h2>
              <div className="mt-4 space-y-3">
                {activity.slice(0, 6).map((item) => (
                  <div
                    key={item.id}
                    className="rounded-2xl border border-slate-200 bg-slate-50 p-3"
                  >
                    <div className="text-sm font-semibold text-slate-800">
                      {item.message}
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      {formatDate(item.created_at)}
                    </div>
                  </div>
                ))}
                {activity.length === 0 && (
                  <div className="text-sm text-slate-500">No activity yet.</div>
                )}
              </div>
            </div>
          </section>
        )}

        {activeTab === "leads" && (
          <section className="mt-8">
            <div className="grid gap-4">
              {leads.map((lead) => {
                const relatedDrafts = draftsByLead[lead.id] || [];
                const latestDraft = relatedDrafts[0];

                return (
                  <div
                    key={lead.id}
                    className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
                  >
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-3">
                          <h3 className="text-xl font-black">{lead.company}</h3>
                          <StatusBadge status={lead.status} />
                          {lead.icp_score && (
                            <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-700">
                              ICP: {lead.icp_score}
                            </span>
                          )}
                          {lead.qualified && (
                            <span
                              className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${
                                lead.qualified === "true"
                                  ? "border-green-200 bg-green-50 text-green-700"
                                  : "border-slate-200 bg-slate-50 text-slate-600"
                              }`}
                            >
                              {lead.qualified === "true"
                                ? "Qualified"
                                : "Not qualified yet"}
                            </span>
                          )}
                        </div>

                        <div className="mt-3 text-sm text-slate-700">
                          <div>
                            <span className="font-semibold">Contact:</span>{" "}
                            {lead.contact_name}
                          </div>
                          <div>
                            <span className="font-semibold">Email:</span>{" "}
                            {lead.email}
                          </div>
                          <div>
                            <span className="font-semibold">Title:</span>{" "}
                            {lead.title || "—"}
                          </div>
                          {lead.industry && (
                            <div>
                              <span className="font-semibold">Industry:</span>{" "}
                              {lead.industry}
                            </div>
                          )}
                          {lead.employee_count && (
                            <div>
                              <span className="font-semibold">
                                Employee count:
                              </span>{" "}
                              {lead.employee_count}
                            </div>
                          )}
                          {lead.location && (
                            <div>
                              <span className="font-semibold">Location:</span>{" "}
                              {lead.location}
                            </div>
                          )}
                          {lead.website && (
                            <div>
                              <span className="font-semibold">Website:</span>{" "}
                              {lead.website}
                            </div>
                          )}
                          <div>
                            <span className="font-semibold">Created:</span>{" "}
                            {formatDate(lead.created_at)}
                          </div>
                          {lead.qualification_reason && (
                            <div className="mt-2 text-xs text-slate-500">
                              {lead.qualification_reason}
                            </div>
                          )}
                          {(lead.research_summary ||
                            lead.pain_points ||
                            lead.personalization_note) && (
                            <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
                              <div className="font-semibold text-slate-800">
                                Research
                              </div>
                              {lead.research_summary && (
                                <div className="mt-1">
                                  <span className="font-semibold">
                                    Summary:
                                  </span>{" "}
                                  {lead.research_summary}
                                </div>
                              )}
                              {lead.pain_points && (
                                <div className="mt-1">
                                  <span className="font-semibold">
                                    Pain points:
                                  </span>{" "}
                                  {lead.pain_points}
                                </div>
                              )}
                              {lead.personalization_note && (
                                <div className="mt-1">
                                  <span className="font-semibold">
                                    Personalization:
                                  </span>{" "}
                                  {lead.personalization_note}
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {latestDraft && (
                          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                            <div className="text-sm font-semibold text-slate-800">
                              Latest Draft
                            </div>
                            <div className="mt-1 text-sm text-slate-600">
                              {latestDraft.subject}
                            </div>
                            <div className="mt-2">
                              <StatusBadge status={latestDraft.status} />
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="flex flex-wrap gap-3">
                        <button
                          onClick={() => handleResearchLead(lead.id)}
                          className="rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm font-bold text-slate-900 hover:bg-slate-100 disabled:opacity-50"
                          disabled={loading}
                        >
                          Research
                        </button>

                        <button
                          onClick={() => handleGenerateResearchedDraft(lead.id)}
                          className="rounded-2xl border border-sky-300 bg-sky-600 px-4 py-3 text-sm font-bold text-white hover:bg-sky-700 disabled:opacity-50"
                          disabled={loading}
                        >
                          Generate Draft from Research
                        </button>

                        <button
                          onClick={() => handleCreateDraft(lead.id)}
                          className="rounded-2xl bg-sky-600 px-4 py-3 text-sm font-bold text-white hover:bg-sky-700 disabled:opacity-50"
                          disabled={loading || lead.status === "sent"}
                        >
                          Create Draft
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}

              {leads.length === 0 && (
                <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
                  No leads yet. Click{" "}
                  <span className="font-bold">Generate Leads</span> to start.
                </div>
              )}
            </div>
          </section>
        )}

        {activeTab === "drafts" && (
          <section className="mt-8">
            <div className="grid gap-4">
              {drafts.map((draft) => (
                <div
                  key={draft.id}
                  className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="max-w-3xl">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="text-xl font-black">{draft.company}</h3>
                        <StatusBadge status={draft.status} />
                        <DeliveryBadge status={draft.delivery_status} />
                      </div>

                      <div className="mt-3 text-sm text-slate-700">
                        <div>
                          <span className="font-semibold">To:</span>{" "}
                          {draft.contact_name} ({draft.email})
                        </div>
                        <div>
                          <span className="font-semibold">Subject:</span>{" "}
                          {draft.subject}
                        </div>
                        <div>
                          <span className="font-semibold">Created:</span>{" "}
                          {formatDate(draft.created_at)}
                        </div>
                        {draft.approved_at && (
                          <div>
                            <span className="font-semibold">Approved:</span>{" "}
                            {formatDate(draft.approved_at)}
                          </div>
                        )}
                        {draft.sent_at && (
                          <div>
                            <span className="font-semibold">Sent:</span>{" "}
                            {formatDate(draft.sent_at)}
                          </div>
                        )}
                        {draft.delivery_status === "failed" &&
                          draft.delivery_error && (
                            <div className="mt-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                              <span className="font-semibold">
                                Delivery error:
                              </span>{" "}
                              {draft.delivery_error}
                            </div>
                          )}
                      </div>

                      {editingDraftId === draft.id ? (
                        <div className="mt-4 space-y-3">
                          <div>
                            <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
                              Subject
                            </div>
                            <input
                              value={draftSubject}
                              onChange={(e) => setDraftSubject(e.target.value)}
                              className="mt-1 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900"
                            />
                          </div>
                          <div>
                            <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
                              Body
                            </div>
                            <textarea
                              value={draftBody}
                              onChange={(e) => setDraftBody(e.target.value)}
                              rows={10}
                              className="mt-1 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900"
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 whitespace-pre-wrap text-sm text-slate-800">
                          {draft.body}
                        </div>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-3">
                      {editingDraftId === draft.id ? (
                        <button
                          onClick={handleSaveDraftEdits}
                          className="rounded-2xl bg-sky-600 px-4 py-3 text-sm font-bold text-white hover:bg-sky-700 disabled:opacity-50"
                          disabled={loading}
                        >
                          Save
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStartEditDraft(draft)}
                          className="rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm font-bold text-slate-900 hover:bg-slate-100 disabled:opacity-50"
                          disabled={loading || draft.status !== "pending"}
                        >
                          Edit
                        </button>
                      )}

                      <button
                        onClick={() => handleApproveDraft(draft.id)}
                        className="rounded-2xl border border-green-300 bg-green-50 px-4 py-3 text-sm font-bold text-green-700 hover:bg-green-100 disabled:opacity-50"
                        disabled={loading || draft.status !== "pending"}
                      >
                        Approve
                      </button>

                      <button
                        onClick={() => handleSendDraft(draft.id)}
                        className="rounded-2xl border border-slate-900 bg-slate-900 px-4 py-3 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
                        disabled={loading || draft.status !== "approved"}
                      >
                        Send
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {drafts.length === 0 && (
                <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
                  No drafts yet. Create a draft from the Leads tab.
                </div>
              )}
            </div>
          </section>
        )}

        {activeTab === "activity" && (
          <section className="mt-8">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-black">Activity Feed</h2>
              <div className="mt-4 space-y-3">
                {activity.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <div className="text-sm font-semibold text-slate-800">
                      {item.message}
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      {formatDate(item.created_at)}
                    </div>
                  </div>
                ))}
                {activity.length === 0 && (
                  <div className="text-sm text-slate-500">No activity yet.</div>
                )}
              </div>
            </div>
          </section>
        )}

        {activeTab === "agents" && (
          <section className="mt-8">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-black">Agents</h2>
              <p className="mt-2 text-sm text-slate-600">
                These are the agents running your workflows.
              </p>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                {agents.map((agent) => (
                  <div
                    key={agent.id}
                    className="rounded-3xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <div className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                      {agent.role}
                    </div>
                    <div className="mt-1 text-lg font-black text-slate-900">
                      {agent.name}
                    </div>
                    <div className="mt-2 text-xs font-semibold text-slate-500">
                      Status:{" "}
                      <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700">
                        {agent.status}
                      </span>
                    </div>
                    {agent.connected_tools && (
                      <div className="mt-2 text-xs text-slate-600">
                        <span className="font-semibold">Tools:</span>{" "}
                        {agent.connected_tools}
                      </div>
                    )}
                    <div className="mt-2 text-[11px] text-slate-500">
                      Created {formatDate(agent.created_at)}
                    </div>
                  </div>
                ))}
                {agents.length === 0 && (
                  <div className="text-sm text-slate-500">
                    No agents yet. They will appear here once the backend seeds
                    them.
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {activeTab === "monitoring" && (
          <section className="mt-8">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-black">Agent Monitoring</h2>
              <p className="mt-2 text-sm text-slate-600">
                High-level view of what each agent has been doing.
              </p>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-500">
                    <tr>
                      <th className="px-4 py-2">Agent</th>
                      <th className="px-4 py-2">Role</th>
                      <th className="px-4 py-2">Tasks</th>
                      <th className="px-4 py-2">Hours Saved</th>
                      <th className="px-4 py-2">Revenue Impact</th>
                      <th className="px-4 py-2">Errors</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {agentStats.map((row) => (
                      <tr key={row.agent_id} className="bg-white">
                        <td className="px-4 py-3 font-semibold text-slate-900">
                          {row.name}
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          {row.role}
                        </td>
                        <td className="px-4 py-3 text-slate-900">
                          {row.tasks}
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          {row.hours_saved.toFixed(1)} hrs
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          ${row.revenue_impact.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          {row.errors}
                        </td>
                      </tr>
                    ))}
                    {agentStats.length === 0 && (
                      <tr>
                        <td
                          colSpan={6}
                          className="px-4 py-4 text-sm text-slate-500"
                        >
                          No agent activity yet. Create and send some drafts to
                          see activity here.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {activeTab === "governance" && (
          <section className="mt-8">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-black">AI Governance & Alerts</h2>
              <p className="mt-2 text-sm text-slate-600">
                Safety, access, and error events across your agents.
              </p>
              <div className="mt-4 space-y-3">
                {governanceEvents.map((e) => (
                  <div
                    key={e.id}
                    className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-slate-900">
                        {e.event_type.toUpperCase()} &mdash; {e.agent_id}
                      </div>
                      <div className="text-xs text-slate-500">
                        {formatDate(e.created_at)}
                      </div>
                    </div>
                    {e.task_name && (
                      <div className="mt-1 text-xs text-slate-600">
                        Task: {e.task_name}
                      </div>
                    )}
                    {e.status && (
                      <div className="mt-1 text-xs text-slate-600">
                        Status: {e.status}
                      </div>
                    )}
                    {e.error_message && (
                      <div className="mt-2 text-xs text-red-700">
                        Error: {e.error_message}
                      </div>
                    )}
                    {e.details && (
                      <div className="mt-2 text-xs text-slate-700">
                        {e.details}
                      </div>
                    )}
                  </div>
                ))}
                {governanceEvents.length === 0 && (
                  <div className="text-sm text-slate-500">
                    No governance alerts yet.
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {activeTab === "roi" && (
          <section className="mt-8">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-black">AI ROI</h2>
              <p className="mt-2 text-sm text-slate-600">
                High-level impact from all agents.
              </p>
              {roiSummary ? (
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <StatCard
                    label="Total Hours Saved"
                    value={`${roiSummary.total_hours_saved.toFixed(1)} hrs`}
                  />
                  <StatCard
                    label="Total Revenue Impact"
                    value={`$${roiSummary.total_revenue_impact.toFixed(2)}`}
                  />
                  <StatCard
                    label="Sales Emails Sent (Agent)"
                    value={roiSummary.sales_emails_sent}
                  />
                </div>
              ) : (
                <div className="mt-4 text-sm text-slate-500">
                  No ROI data yet.
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}