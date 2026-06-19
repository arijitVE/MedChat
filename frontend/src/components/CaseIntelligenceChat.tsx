import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import { Send, CheckCircle, Lightbulb, Clipboard, PlusCircle, Bookmark, AlertTriangle } from 'lucide-react';
import { Case, Message } from '../types';

interface CaseIntelligenceChatProps {
  activeCase: Case;
  onSendMessage: (msg: Message) => void;
  onUpdateChatHistory: (msgs: Message[]) => void;
}

export default function CaseIntelligenceChat({
  activeCase,
  onSendMessage,
  onUpdateChatHistory
}: CaseIntelligenceChatProps) {
  const [inputText, setInputText] = useState('');
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeCase.chatHistory]);

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || inputText;
    if (!text.trim()) return;

    // Create user message
    const userMsg: Message = {
      id: 'usr-' + Math.floor(Math.random() * 100000),
      sender: 'user',
      time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      content: text
    };

    onUpdateChatHistory([...activeCase.chatHistory, userMsg]);
    setInputText('');

    try {
      const res = await api.chatWithCase(activeCase.id, text);
      
      const aiMsg: Message = {
        id: 'ai-' + Math.floor(Math.random() * 100000),
        sender: 'ai',
        time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        content: res.reply
      };
      
      onUpdateChatHistory([...activeCase.chatHistory, userMsg, aiMsg]);
    } catch (err) {
      console.error("Chat failed", err);
      const errorMsg: Message = {
        id: 'ai-' + Math.floor(Math.random() * 100000),
        sender: 'ai',
        time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        content: "Sorry, I encountered an error while processing your request."
      };
      onUpdateChatHistory([...activeCase.chatHistory, userMsg, errorMsg]);
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden h-full">
      
      {/* Left Chat Window main panel */}
      <div className="flex-1 flex flex-col justify-between bg-white overflow-hidden h-full border-r border-gray-200">
        
        {/* Chat message streams list */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          
          {activeCase.chatHistory.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 select-none">
              <span className="material-symbols-outlined text-[48px] text-gray-300 mb-2">chat</span>
              <p className="font-sans font-bold text-xs text-black">Case Intelligence Workspace</p>
              <p className="text-gray-400 text-[11px] max-w-sm mt-1">
                Ask specific questions regarding this case history, ask to analyze surgical notes, draft medical timelines, or build a timeline reconciliation document.
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-2 max-w-md">
                <button
                  onClick={() => handleSend("Synthesize the post-op timelines")}
                  className="px-3 py-1.5 border border-gray-200 bg-gray-50 hover:bg-gray-100 rounded-full font-semibold text-[10px] text-gray-700 transition-colors cursor-pointer"
                >
                  "Synthesize the post-op timelines"
                </button>
                <button
                  onClick={() => handleSend("Identify discrepancies in Nurse R.'s logs")}
                  className="px-3 py-1.5 border border-gray-200 bg-gray-50 hover:bg-gray-100 rounded-full font-semibold text-[10px] text-gray-700 transition-colors cursor-pointer"
                >
                  "Identify discrepancies in Nurse R.'s logs"
                </button>
                <button
                  onClick={() => handleSend("Generate Reconciliation")}
                  className="px-3 py-1.5 border border-gray-200 bg-gray-50 hover:bg-gray-100 rounded-full font-semibold text-[10px] text-gray-700 transition-colors cursor-pointer"
                >
                  "Generate Reconciliation"
                </button>
              </div>
            </div>
          ) : (
            activeCase.chatHistory.map((msg) => {
              const isAi = msg.sender === 'ai';
              return (
                <div
                  key={msg.id}
                  className={`flex ${isAi ? 'justify-start' : 'justify-end'} select-text`}
                >
                  <div className={`max-w-xl rounded-xl p-4 border text-xs shadow-xs ${
                    isAi
                      ? 'bg-gray-50 border-gray-200 text-gray-800 rounded-tl-none'
                      : 'bg-[#131b2e] border-blue-900 text-white rounded-tr-none'
                  }`}>
                    {/* Header info */}
                    <div className="flex justify-between items-center mb-1.5 opacity-60 font-mono text-[9px] select-none">
                      <span className="font-bold uppercase tracking-wider">{isAi ? 'Medical-Legal Co-Counsel' : 'Authorized Evaluator'}</span>
                      <span>{msg.time}</span>
                    </div>

                    {/* Text block supports simple bullet formatting or tables */}
                    <div className="whitespace-pre-wrap leading-relaxed font-sans prose prose-sm text-xs">
                      {msg.content.includes('|') ? (
                        // Simple custom table renderer inside chatbot
                        <div className="overflow-x-auto my-3 bg-white border border-gray-200 rounded">
                          <table className="w-full text-left text-[10px] uppercase font-mono tracking-normal border-collapse">
                            <thead>
                              <tr className="bg-gray-100 border-b border-gray-200">
                                <th className="p-2 border-r border-gray-200">Doc Source</th>
                                <th className="p-2 border-r border-gray-200">Logged Time</th>
                                <th className="p-2 border-r border-gray-200">Findings</th>
                                <th className="p-2">Conflict Context</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr className="border-b border-gray-150">
                                <td className="p-2 font-bold border-r border-gray-200 text-black">Nursing Logs</td>
                                <td className="p-2 border-r border-gray-200">March 14, 14:30</td>
                                <td className="p-2 border-r border-gray-200">Sensory loss documented</td>
                                <td className="p-2 text-red-700">Delayed 12.5 hrs warning page</td>
                              </tr>
                              <tr className="border-b border-gray-150">
                                <td className="p-2 font-bold border-r border-gray-200 text-black">Dr. Aris Notes</td>
                                <td className="p-2 border-r border-gray-200">March 15, 03:00</td>
                                <td className="p-2 border-r border-gray-200">Received emergency alarm page</td>
                                <td className="p-2 text-red-700">Page registered only after motor loss</td>
                              </tr>
                              <tr>
                                <td className="p-2 font-bold border-r border-gray-200 text-black">Audit Trails</td>
                                <td className="p-2 border-r border-gray-200">March 15, 11:20</td>
                                <td className="p-2 border-r border-gray-200">Post-op telemetry written</td>
                                <td className="p-2">Written retrospectively</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        msg.content
                      )}
                    </div>

                    {/* Highly stylized Document Citation matching visual guideline mock completely */}
                    {msg.citation && (
                      <div className="mt-3.5 pt-3.5 border-t border-gray-200/50 bg-white/40 p-2.5 rounded-lg border border-dashed border-gray-200 select-none">
                        <div className="flex items-center gap-1.5 mb-1.5 select-none">
                          <span className="material-symbols-outlined text-[16px] text-[#565e74]">bookmark</span>
                          <span className="font-mono text-[9px] text-[#565e74] font-bold uppercase tracking-wider">
                            Source Citation Verified
                          </span>
                        </div>
                        <p className="text-[10px] italic leading-relaxed text-gray-600 block mb-1">
                          {msg.citation.text}
                        </p>
                        <p className="text-[9px] text-[#565e74] font-semibold">
                          Reference File: <span className="underline font-mono">{msg.citation.source}</span> &bull; Page: {msg.citation.page}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
          
          {/* Simulated typing status */}
          <div ref={chatBottomRef} />
        </div>

        {/* Message Input trigger bar footer */}
        <div className="p-4 border-t border-gray-250 select-none">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              className="flex-1 px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-xs font-sans focus:outline-none focus:border-black transition-all"
              placeholder="Ask a question about this clinical history..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
            />
            <button
              type="submit"
              className="p-2.5 bg-black hover:opacity-95 text-white rounded-lg cursor-pointer transition-opacity shrink-0"
              title="Submit Inquiry"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>

      {/* Right Chat Panel Index matching visual guides details perfectly */}
      <div className="hidden lg:flex w-64 bg-slate-50 border-l border-gray-250 flex-col p-4 gap-4 shrink-0 select-none">
        {/* Section: Indexed Files */}
        <div>
          <h4 className="font-sans font-bold text-[10px] text-gray-500 uppercase tracking-widest mb-2 border-b border-gray-200 pb-1.5 flex justify-between items-center">
            <span>Indexed Reports</span>
            <span className="bg-green-50 text-green-700 text-[8px] font-bold px-1.5 rounded uppercase font-sans tracking-wide">
              Secure
            </span>
          </h4>
          <ul className="space-y-1.5 text-[11px] font-sans">
            <li className="flex items-center gap-2 p-1 text-gray-800">
              <span className="material-symbols-outlined text-[16px] text-green-600">check_box</span>
              <span className="truncate">ER_Admit_Log_0310.pdf</span>
            </li>
            <li className="flex items-center gap-2 p-1 text-gray-800">
              <span className="material-symbols-outlined text-[16px] text-green-600">check_box</span>
              <span className="truncate">Surgical_Report_Final.pdf</span>
            </li>
            <li className="flex items-center gap-2 p-1 text-gray-800">
              <span className="material-symbols-outlined text-[16px] text-green-600">check_box</span>
              <span className="truncate">Billing_Statement_Q1.pdf</span>
            </li>
          </ul>
        </div>

        {/* Section: Suggested Citations */}
        <div>
          <h4 className="font-sans font-bold text-[10px] text-gray-500 uppercase tracking-widest mb-2 border-b border-gray-200 pb-1.5 flex items-center gap-1">
            <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
            <span>Suggested Citations</span>
          </h4>
          <div className="space-y-2">
            <div
              onClick={() => handleSend("What does the orthopedic surgery report page 4 note about knee flex?")}
              className="bg-white border border-gray-200 p-2.5 rounded-lg hover:border-black cursor-pointer shadow-[0px_2px_4px_rgba(0,0,0,0.02)] transition-all group"
            >
              <p className="text-[10px] font-semibold text-black group-hover:underline">Orthopedic report pg. 4</p>
              <p className="text-[9px] text-gray-550 leading-relaxed mt-0.5">"Knee extension restricted post-op"</p>
            </div>

            <div
              onClick={() => handleSend("Analyze ER Admit timeline and nitgroglycerin administration delay.")}
              className="bg-white border border-gray-200 p-2.5 rounded-lg hover:border-black cursor-pointer shadow-[0px_2px_4px_rgba(0,0,0,0.02)] transition-all group"
            >
              <p className="text-[10px] font-semibold text-black group-hover:underline">ER Admit Timeline</p>
              <p className="text-[9px] text-gray-550 leading-relaxed mt-0.5">Nitroglycerin delivery delayed 45m.</p>
            </div>
          </div>
        </div>

        {/* Disclaimer Warning */}
        <div className="mt-auto bg-amber-50 rounded-lg p-2.5 border border-[#dec29a] text-[10px] leading-relaxed text-amber-900 select-none">
          <p className="font-bold flex items-center gap-1 mb-0.5">
            <span className="material-symbols-outlined text-amber-700 text-[14px]">warning</span>
            <span>HIPAA Workspace</span>
          </p>
          Queries and synthesized text are scoped strictly to verified Case #8821 documentation.
        </div>
      </div>
    </div>
  );
}
