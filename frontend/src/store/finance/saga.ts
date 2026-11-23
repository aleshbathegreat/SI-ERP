import { call, put, takeLatest } from "redux-saga/effects";
import api from "@/lib/api";
import {
  fetchAccountsFailure,
  fetchAccountsRequest,
  fetchAccountsSuccess,
  fetchVendorsFailure,
  fetchVendorsRequest,
  fetchVendorsSuccess,
  type Account,
  type Vendor,
} from "./slice";

function* fetchVendorsWorker() {
  try {
    const { data }: { data: { results?: Vendor[] } | Vendor[] } = yield call(
      api.get,
      "/finance/vendors/"
    );
    yield put(fetchVendorsSuccess(Array.isArray(data) ? data : data.results || []));
  } catch {
    yield put(fetchVendorsFailure("Unable to load vendors"));
  }
}

function* fetchAccountsWorker() {
  try {
    const { data }: { data: { results?: Account[] } | Account[] } = yield call(
      api.get,
      "/finance/accounts/"
    );
    yield put(fetchAccountsSuccess(Array.isArray(data) ? data : data.results || []));
  } catch {
    yield put(fetchAccountsFailure("Unable to load accounts"));
  }
}

export function* financeSaga() {
  yield takeLatest(fetchVendorsRequest.type, fetchVendorsWorker);
  yield takeLatest(fetchAccountsRequest.type, fetchAccountsWorker);
}
