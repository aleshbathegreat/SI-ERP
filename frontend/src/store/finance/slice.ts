import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type Vendor = {
  id: number;
  name: string;
  ntn: string;
  email: string;
  phone: string;
  is_active: boolean;
};

export type Account = {
  id: number;
  code: string;
  name: string;
  account_type: string;
  is_active: boolean;
};

type FinanceState = {
  vendors: Vendor[];
  accounts: Account[];
  loading: boolean;
  error: string | null;
};

const initialState: FinanceState = {
  vendors: [],
  accounts: [],
  loading: false,
  error: null,
};

const financeSlice = createSlice({
  name: "finance",
  initialState,
  reducers: {
    fetchVendorsRequest(state) {
      state.loading = true;
      state.error = null;
    },
    fetchVendorsSuccess(state, action: PayloadAction<Vendor[]>) {
      state.loading = false;
      state.vendors = action.payload;
    },
    fetchVendorsFailure(state, action: PayloadAction<string>) {
      state.loading = false;
      state.error = action.payload;
    },
    fetchAccountsRequest(state) {
      state.loading = true;
      state.error = null;
    },
    fetchAccountsSuccess(state, action: PayloadAction<Account[]>) {
      state.loading = false;
      state.accounts = action.payload;
    },
    fetchAccountsFailure(state, action: PayloadAction<string>) {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const {
  fetchVendorsRequest,
  fetchVendorsSuccess,
  fetchVendorsFailure,
  fetchAccountsRequest,
  fetchAccountsSuccess,
  fetchAccountsFailure,
} = financeSlice.actions;
export default financeSlice.reducer;
