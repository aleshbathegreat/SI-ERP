import { all, fork } from "redux-saga/effects";
import { authSaga } from "./auth/saga";
import { dashboardSaga } from "./dashboard/saga";
import { financeSaga } from "./finance/saga";
import { hrSaga } from "./hr/saga";

export default function* rootSaga() {
  yield all([fork(authSaga), fork(dashboardSaga), fork(hrSaga), fork(financeSaga)]);
}
