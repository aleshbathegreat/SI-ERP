import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type Employee = {
  id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  email: string;
  status: string;
  department_name?: string;
  designation_title?: string;
  basic_salary: string;
};

type HrState = {
  employees: Employee[];
  loading: boolean;
  error: string | null;
};

const initialState: HrState = {
  employees: [],
  loading: false,
  error: null,
};

const hrSlice = createSlice({
  name: "hr",
  initialState,
  reducers: {
    fetchEmployeesRequest(state) {
      state.loading = true;
      state.error = null;
    },
    fetchEmployeesSuccess(state, action: PayloadAction<Employee[]>) {
      state.loading = false;
      state.employees = action.payload;
    },
    fetchEmployeesFailure(state, action: PayloadAction<string>) {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const { fetchEmployeesRequest, fetchEmployeesSuccess, fetchEmployeesFailure } =
  hrSlice.actions;
export default hrSlice.reducer;
