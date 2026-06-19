import React, { useState } from 'react';
import { Lock, Shield, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { api, setAuthToken } from '../api';

interface AuthScreensProps {
  onLoginSuccess: (fullName: string, email: string) => void;
}

export default function AuthScreens({ onLoginSuccess }: AuthScreensProps) {
  const [isLoginTab, setIsLoginTab] = useState(true);
  
  // Prefilled states to match screenshot references
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [agreeToTerms, setAgreeToTerms] = useState(true);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    
    setError(null);
    setIsLoading(true);
    
    try {
      if (isLoginTab) {
        const data = await api.login({ email, password });
        setAuthToken(data.access_token);
      } else {
        const data = await api.signup({ email, password, full_name: fullName });
        setAuthToken(data.access_token);
      }
      
      const me = await api.getMe().catch(() => ({ full_name: fullName || email }));
      
      onLoginSuccess(me.full_name || fullName || 'Dr. Julian Pierce', email);
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  const togglePasswordVisibility = () => {
    setShowPassword(prev => !prev);
  };

  return (
    <div className="min-h-screen bg-[#f4f7f9] flex flex-col justify-between items-center py-12 px-4 select-none font-sans">
      
      {/* Top Header */}
      <div className="text-center mt-6 max-w-lg w-full">
        <h1 className="text-[32px] font-bold text-slate-900 tracking-tight leading-tight">
          MedLegal Review
        </h1>
        <p className="text-sm text-slate-500 mt-2 font-medium">
          {isLoginTab 
            ? 'Secure portal for authorized legal and medical reviewers.'
            : 'Clinical Analysis. Legal Precision.'
          }
        </p>
      </div>

      {/* Main card */}
      <div className="w-full max-w-[430px] bg-white border border-[#e2e8f0] rounded-xl shadow-[0_4px_12px_rgba(0,0,0,0.03)] p-8 my-6 flex flex-col">
        {/* Title inside card (only for sign up, as seen in the mockup) */}
        {!isLoginTab && (
          <h2 className="text-xl font-bold text-slate-900 mb-6 tracking-tight">
            Create Account
          </h2>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {/* Full Name field (Sign Up only) */}
          {!isLoginTab && (
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 font-sans">
                Full Name
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Dr. Julian Pierce"
                className="w-full bg-white border border-[#e2e8f0] rounded-md py-2.5 px-3.5 text-sm w-full outline-none focus:border-slate-500 transition-all font-sans text-slate-800"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
          )}

          {/* Email field */}
          <div>
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 font-sans">
              {isLoginTab ? 'Email Address' : 'Organization Email'}
            </label>
            <input
              type="email"
              required
              placeholder="e.g. j.pierce@medicalcenter.org"
              className="w-full bg-white border border-[#e2e8f0] rounded-md py-2.5 px-3.5 text-sm w-full outline-none focus:border-slate-500 transition-all font-sans text-slate-800"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          {/* Password field */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest font-sans">
                Password
              </label>
              {isLoginTab && (
                <button
                  type="button"
                  onClick={() => alert("Password recovery instructions would be dispatched to authorized secure domain.")}
                  className="text-[10.5px] text-[#2563eb]/80 hover:text-[#1d4ed8] font-medium tracking-wide border-none bg-transparent cursor-pointer hover:underline"
                >
                  Forgot?
                </button>
              )}
            </div>
            
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                placeholder="••••••••••••"
                className="w-full bg-white border border-[#e2e8f0] rounded-md py-2.5 pl-3.5 pr-10 text-sm w-full outline-none focus:border-slate-500 transition-all font-sans text-slate-800"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={togglePasswordVisibility}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors p-1 cursor-pointer border-none bg-transparent flex items-center justify-center"
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
            
            {!isLoginTab && (
              <p className="text-[10px] text-slate-400/90 mt-1 font-sans">
                Must be at least 12 characters with a mix of letters and symbols.
              </p>
            )}
          </div>

          {/* Remember Me / Terms Checkbox */}
          {isLoginTab ? (
            <label className="flex items-center select-none cursor-pointer group mt-0.5">
              <input
                type="checkbox"
                className="w-4 h-4 accent-[#2563eb] rounded border-gray-300 focus:ring-0 cursor-pointer"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
              />
              <span className="text-xs font-medium text-slate-500 ml-2 group-hover:text-slate-700 transition-colors font-sans">
                Remember this device
              </span>
            </label>
          ) : (
            <label className="flex items-start select-none cursor-pointer group mt-0.5">
              <input
                type="checkbox"
                className="w-4 h-4 accent-[#2563eb] rounded border-gray-300 focus:ring-0 cursor-pointer shrink-0 mt-0.5"
                checked={agreeToTerms}
                onChange={(e) => setAgreeToTerms(e.target.checked)}
              />
              <span className="text-xs font-medium text-slate-500 ml-2 leading-tight group-hover:text-slate-700 transition-colors font-sans">
                I agree to the <span className="font-semibold text-slate-900 font-sans">Terms of Service</span> and <span className="font-semibold text-slate-900 font-sans">Privacy Policy</span>.
              </span>
            </label>
          )}

          {/* Error Message */}
          {error && (
            <div className="text-red-500 text-xs text-center font-medium bg-red-50 p-2 rounded border border-red-100">
              {error}
            </div>
          )}

          {/* Submit Action */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-black hover:bg-neutral-900 text-white font-semibold py-3 px-4 rounded-lg text-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer mt-2 disabled:opacity-50"
          >
            <span>{isLoading ? 'Processing...' : (isLoginTab ? 'Sign In' : 'Create Workspace')}</span>
            {!isLoading && isLoginTab && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        {/* Divider */}
        <div className="border-t border-slate-100 my-5"></div>

        {/* Tab Switcher */}
        <div className="text-center">
          <p className="text-xs text-slate-400 font-sans">
            {isLoginTab ? "Don't have an account yet?" : "Already have an account?"}
          </p>
          <button
            onClick={() => setIsLoginTab(!isLoginTab)}
            className="text-sm font-bold text-slate-900 hover:underline cursor-pointer tracking-tight mt-1.5 border-none bg-transparent inline-block font-sans"
          >
            {isLoginTab ? 'Create Account' : 'Sign In'}
          </button>
        </div>
      </div>

      {/* Footer Security Compliance block */}
      <footer className="mb-4 flex items-center justify-center gap-6 text-slate-400/90 text-[10.5px] font-bold uppercase tracking-widest font-sans">
        <div className="flex items-center gap-1.5">
          <Lock className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-bold">256-Bit Encryption</span>
        </div>
        <div className="text-slate-300">|</div>
        <div className="flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-bold">HIPAA Compliant</span>
        </div>
      </footer>
    </div>
  );
}
