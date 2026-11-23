import { call, put, takeLatest } from "redux-saga/effects";
import api from "@/lib/api";
import {
  fetchDashboardFailure,
  fetchDashboardRequest,
  fetchDashboardSuccess,
  type DashboardStats,
} from "./slice";

function* fetchDashboardWorker() {
  try {
    const { data }: { data: DashboardStats } = yield call(api.get, "/dashboard/");
    yield put(fetchDashboardSuccess(data));
  } catch {
    yield put(fetchDashboardFailure("Unable to load dashboard"));
  }
}

export function* dashboardSaga() {
  yield takeLatest(fetchDashboardRequest.type, fetchDashboardWorker);
}
