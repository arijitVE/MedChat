import { useState, useRef, useEffect } from 'react';
import { Search, Bell, Settings, LogOut } from 'lucide-react';
import { User } from '../types';

interface HeaderProps {
  currentTab: string;
  activeCaseId: string | null;
  caseName?: string;
  onNavigateHome: () => void;
  currentUser: User;
  onLogout: () => void;
  searchTerm: string;
  onSearchChange: (val: string) => void;
  statusFilter: 'ALL' | 'PROCESSING' | 'COMPLETED';
  onStatusFilterChange: (filter: 'ALL' | 'PROCESSING' | 'COMPLETED') => void;
  processingCount: number;
  completedCount: number;
  onOpenAdmin?: () => void;
}

export default function Header({
  currentTab,
  activeCaseId,
  caseName,
  onNavigateHome,
  currentUser,
  onLogout,
  searchTerm,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  processingCount,
  completedCount,
  onOpenAdmin,
}: HeaderProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <header className="bg-white border-b border-gray-200/80 z-50 sticky top-0 flex justify-between items-center px-6 w-full h-16">
      <div className="flex items-center gap-8 h-full">
        <h1
          className="font-sans text-lg font-bold text-black cursor-pointer hover:opacity-80 transition-opacity whitespace-nowrap"
          onClick={() => {
            onStatusFilterChange('ALL');
            onNavigateHome();
          }}
        >
          MedLegal Review
        </h1>
        
        <div className="hidden md:flex items-center gap-1 h-full">
          <nav className="flex gap-6 h-full items-center">
            <button
              onClick={() => {
                onStatusFilterChange('ALL');
                onNavigateHome();
              }}
              className={`text-sm tracking-tight cursor-pointer transition-all h-full flex items-center px-1 border-b-2 mt-[2px] ${
                statusFilter === 'ALL' && !activeCaseId
                  ? 'text-black font-bold border-black'
                  : 'text-[#5e7e9a] hover:text-black font-semibold border-transparent'
              }`}
            >
              Cases
            </button>
            <button
              onClick={() => {
                onStatusFilterChange('PROCESSING');
                onNavigateHome();
              }}
              className={`text-sm tracking-tight cursor-pointer transition-all h-full flex items-center px-1 border-b-2 mt-[2px] ${
                statusFilter === 'PROCESSING' && !activeCaseId
                  ? 'text-black font-bold border-black'
                  : 'text-[#5e7e9a] hover:text-black font-semibold border-transparent'
              }`}
            >
              Processing ({processingCount})
            </button>
            <button
              onClick={() => {
                onStatusFilterChange('COMPLETED');
                onNavigateHome();
              }}
              className={`text-sm tracking-tight cursor-pointer transition-all h-full flex items-center px-1 border-b-2 mt-[2px] ${
                statusFilter === 'COMPLETED' && !activeCaseId
                  ? 'text-black font-bold border-black'
                  : 'text-[#5e7e9a] hover:text-black font-semibold border-transparent'
              }`}
            >
              Completed ({completedCount})
            </button>
          </nav>
        </div>

        {activeCaseId && (
          <div className="hidden lg:flex items-center gap-2 text-gray-500 font-sans text-xs">
            <span className="w-[1.5px] h-4 bg-gray-300 mx-1"></span>
            <span className="text-gray-400">Workspace:</span>
            <span className="text-black font-semibold truncate max-w-[160px]">{caseName || `Case #${activeCaseId}`}</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Search Input */}
        <div className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            className="pl-9 pr-4 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs w-64 focus:outline-none focus:border-black transition-all"
            placeholder={activeCaseId ? "Search case documents..." : "Search cases..."}
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>

        {/* Notifications Icon with Indicator */}
        <div className="relative">
          <button className="text-gray-500 hover:bg-gray-100 p-1.5 rounded-full transition-colors cursor-pointer relative">
            <Bell className="w-5 h-5 text-gray-600" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#ba1a1a] rounded-full border border-white"></span>
          </button>
        </div>

        {/* Settings Icon - Only visible for admin users */}
        {onOpenAdmin && (
          <button 
            className="text-gray-500 hover:bg-gray-100 p-1.5 rounded-full transition-colors cursor-pointer"
            onClick={() => onOpenAdmin()}
            title="Open System Administration Panel"
          >
            <Settings className="w-5 h-5 text-gray-600" />
          </button>
        )}

        {/* User Info & Avatar */}
        <div 
          ref={dropdownRef}
          className="relative flex items-center gap-2 border-l border-gray-200 pl-4 cursor-pointer select-none"
          onClick={() => setIsDropdownOpen(prev => !prev)}
        >
          <div className="hidden lg:flex flex-col items-end">
            <span className="text-xs font-semibold text-gray-800 truncate max-w-[120px]">
              {currentUser.fullName}
            </span>
            <button
              className="text-[10px] text-gray-400 hover:text-black hover:underline cursor-pointer"
              onClick={(e) => {
                e.stopPropagation();
                setIsDropdownOpen(prev => !prev);
              }}
            >
              My Account
            </button>
          </div>
          <div className="w-8 h-8 rounded-full border border-gray-300 overflow-hidden shrink-0 hover:ring-2 hover:ring-black/5 transition-all">
            <img
              className="w-full h-full object-cover"
              alt="Profile"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDImr28oa8kceqrI3cyhYOvJZr8msv4xOqNhfpyFA4zI79BrvvbIEUvTTg79fqybHt1P8Ht0HKeed8LDz-8Vm1Xu1FH94TDDkMlAFF_Cjxgr6AbiJrLZtAgj2zsfRS1hAO-WSpKCDzhXR_T1pwmYQIKrflgbQRGOCZfj31E78-P6fw2VlAeBlUbf4fJQfGXtvPzK4QljK3n5p52SBWbP3gZmXH6eHoubVDV8VNVctZfcq5T5FMosreOWLLVJYkn8ZRZbjMf9qo15XO-"
            />
          </div>

          {/* Dropdown Menu */}
          {isDropdownOpen && (
            <div 
              className="absolute right-0 top-12 mt-1.5 w-64 bg-white border border-gray-200/80 rounded-xl shadow-lg z-50 text-left cursor-default overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-4 flex flex-col bg-gray-50/50">
                <div className="font-sans text-sm font-semibold text-gray-900">
                  {currentUser.fullName}
                </div>
                <div className="font-sans text-xs text-gray-400 mt-0.5">
                  {currentUser.email}
                </div>
              </div>
              {onOpenAdmin && (
                <>
                  <div className="border-t border-gray-100"></div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsDropdownOpen(false);
                      onOpenAdmin();
                    }}
                    className="w-full text-left px-4 py-3 flex items-center gap-2.5 text-indigo-600 hover:bg-slate-50 font-sans text-sm transition-colors cursor-pointer border-none"
                  >
                    <Settings className="w-4 h-4 text-indigo-500" />
                    <span className="font-medium text-[13px]">Admin Control Center</span>
                  </button>
                </>
              )}
              <div className="border-t border-gray-100"></div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setIsDropdownOpen(false);
                  onLogout();
                }}
                className="w-full text-left px-4 py-3 flex items-center gap-2.5 text-red-600 hover:bg-slate-50 font-sans text-sm transition-colors cursor-pointer border-none"
              >
                <LogOut className="w-4 h-4 text-red-500" />
                <span className="font-medium text-[13px]">Log Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
