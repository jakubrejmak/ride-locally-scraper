import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ToastProvider } from "./components/toast/ToastContext";
import Login from "./pages/login/page";
import Home from "./pages/home/page";

function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}

export default App;
