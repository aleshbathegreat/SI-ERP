import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type StatusCount = { status: string; count: number };
export type MixItem = { label: string; value: number; color?: string };
export type Sentiment = {
  tone: "positive" | "calm" | "attention";
  title: string;
  detail: string;
};
export type TrendPoint = { label: string; journals: number; payslips: number };

export type DashboardStats = {
  employees: number;
  active_employees?: number;
  vendors: number;
  accounts: number;
  pending_leaves: number;
  open_payroll_periods: number;
  approved_leaves?: number;
  module_mix?: MixItem[];
  leave_status?: StatusCount[];
  journal_status?: StatusCount[];
  ap_status?: StatusCount[];
  payroll_status?: StatusCount[];
  budget?: { total: string; utilized: string; pct: number };
  attendance_month?: {
    present: number;
    absent: number;
    late: number;
    other: number;
  };
  trend_6m?: TrendPoint[];
  sentiments?: Sentiment[];
  health_score?: number;
};

type DashboardState = {
  stats: DashboardStats | null;
  loading: boolean;
  error: string | null;
};

const initialState: DashboardState = {
  stats: null,
  loading: false,
  error: null,
};

const dashboardSlice = createSlice({
  name: "dashboard",
  initialState,
  reducers: {
    fetchDashboardRequest(state) {
      state.loading = true;
      state.error = null;
    },
    fetchDashboardSuccess(state, action: PayloadAction<DashboardStats>) {
      state.loading = false;
      state.stats = action.payload;
    },
    fetchDashboardFailure(state, action: PayloadAction<string>) {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const { fetchDashboardRequest, fetchDashboardSuccess, fetchDashboardFailure } =
  dashboardSlice.actions;
export default dashboardSlice.reducer;
