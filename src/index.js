import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from "react-router-dom";
import './index.css';
import App from './App';
import App2 from './App2';
import App3 from './App3';
import reportWebVitals from './reportWebVitals';
import { configureStore} from '@reduxjs/toolkit';
import myreducer from './store/reducer';
import {ThemeProvider} from '@mui/material/styles';
import { Provider } from 'react-redux';
import outerTheme from './theme/theme';
import 'font-awesome/css/font-awesome.min.css';

const store=configureStore({
  reducer: myreducer,
  middleware: (getDefaultMiddleware) => getDefaultMiddleware({
    immutableCheck: false,
    serializableCheck: false,
  })
});

const root = createRoot(document.getElementById('root'));
root.render(
  <Provider store={store}>
    <ThemeProvider theme={outerTheme}>
      <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}></Route>
        <Route path="/experiments" element={<App2 />}></Route>
        <Route path="/sensitivity_analysis" element={<App3 />}></Route>
      </Routes>
      </BrowserRouter>
     {/* <App /> */}
    </ThemeProvider>
  </Provider>
);


// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
