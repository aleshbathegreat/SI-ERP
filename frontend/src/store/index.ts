import { configureStore } from "@reduxjs/toolkit";
import createSagaMiddleware from "redux-saga";
import authReducer from "./auth/slice";
import dashboardReducer from "./dashboard/slice";
import financeReducer from "./finance/slice";
import hrReducer from "./hr/slice";
import rootSaga from "./rootSaga";

const sagaMiddleware = createSagaMiddleware();

export const makeStore = () => {
  const store = configureStore({
    reducer: {
      auth: authReducer,
      dashboard: dashboardReducer,
      hr: hrReducer,
      finance: financeReducer,
    },
    middleware: (getDefault) => getDefault({ thunk: false }).concat(sagaMiddleware),
  });
  sagaMiddleware.run(rootSaga);
  return store;
};

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
