import { call, put, takeLatest } from "redux-saga/effects";
import api from "@/lib/api";
import {
  fetchEmployeesFailure,
  fetchEmployeesRequest,
  fetchEmployeesSuccess,
  type Employee,
} from "./slice";

function* fetchEmployeesWorker() {
  try {
    const { data }: { data: { results?: Employee[] } | Employee[] } = yield call(
      api.get,
      "/hr/employees/"
    );
    const list = Array.isArray(data) ? data : data.results || [];
    yield put(fetchEmployeesSuccess(list));
  } catch {
    yield put(fetchEmployeesFailure("Unable to load employees"));
  }
}

export function* hrSaga() {
  yield takeLatest(fetchEmployeesRequest.type, fetchEmployeesWorker);
}
