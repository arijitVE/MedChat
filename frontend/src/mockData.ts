import { Case } from './types';

export const INITIAL_CASES: Case[] = [
  {
    id: '8821',
    title: 'Johnson vs. Medical Center',
    ref: '8821-XP',
    clientName: 'Robert Johnson',
    clientAgeSex: '58-year-old male',
    primaryDiagnosis: ['Chronic Hypertension', 'Type 2 Diabetes'],
    status: 'COMPLETED',
    dateCreated: 'Oct 24, 2023',
    documents: [
      {
        id: 'doc-1',
        name: 'Radiology_Report_01-22.pdf',
        uuid: '8821-RAD-001',
        size: '1.2 MB',
        uploadedAt: 'Jan 12, 2024',
        status: 'PROCESSED'
      },
      {
        id: 'doc-2',
        name: 'Surgical_Notes_Final.docx',
        uuid: '8821-SUR-012',
        size: '456 KB',
        uploadedAt: 'Jan 14, 2024',
        status: 'PROCESSED'
      },
      {
        id: 'doc-3',
        name: 'Hospital_Discharge_Summary.pdf',
        uuid: '8821-HOS-003',
        size: '2.4 MB',
        uploadedAt: 'Jan 15, 2024',
        status: 'PROCESSED'
      },
      {
        id: 'doc-4',
        name: 'Corrupted_Imaging_Data.zip',
        uuid: '8821-IMG-044',
        size: '89 MB',
        uploadedAt: 'Jan 15, 2024',
        status: 'FAILED'
      }
    ],
    summary: {
      updatedAt: 'Oct 24, 2023',
      version: 'V2.4 GENERATED',
      patientName: 'Robert Johnson',
      patientAgeSex: '58-year-old male',
      diagnoses: ['Chronic Hypertension', 'Type 2 Diabetes'],
      insights: [
        'Stable cardiac rhythm documented across all 2021 outpatient visits; however, progressive decrease in renal function observed starting Q3 2022.',
        'Consistent non-compliance with diet and medication reported during hospitalization periods in late 2022.',
        'Medical imaging from June 2023 indicates significant calcification of the aortic arch, not present in the 2021 baseline scans.'
      ],
      narrative: 'On Feb 14, 2022, the patient presented at St. Jude Emergency with acute chest pain. Clinical logs indicate a delayed administration of sublingual nitroglycerin (approx. 45-minute wait). Primary physician noted moderate respiratory distress, stabilizing after 4 hours. No surgical intervention was performed during this episode.',
      medications: ['Lisinopril', 'Metformin']
    },
    opinion: {
      version: '1.4',
      lastAnalyzed: 'Oct 24, 2023',
      executiveSummary: "Pursuant to the request for a medical-legal review regarding the case of Johnson vs. Medical Center, this preliminary opinion outlines the findings based on provided medical documentation from 2021-2023. The focus of this inquiry centers on the standard of care provided during the postoperative period following the patient's spinal fusion on March 12, 2022.",
      standardsOfCare: [
        'Neurological assessments every 4 hours for the first 48 hours post-op.',
        'Immediate physician notification if motor strength decreased by >1 grade on the MMT scale.',
        'Continuous pulse oximetry and hemodynamic monitoring.'
      ],
      chronology: 'At 14:30 on March 14, Nurse R. recorded a shift in sensation in the lower extremities. However, the attending neurosurgeon was not paged until 03:00 the following morning. (Ref: Nursing Log, pg. 42)',
      causation: "It is the opinion of this analysis that the delay in surgical intervention to address the epidural hematoma—facilitated by the lack of timely communication between nursing staff and the surgical team—was the primary contributing factor to the patient's long-term mobility impairment.",
      furtherInquiry: [
        'Complete shift rosters for the nursing station on the nights of March 13-15.',
        'Audit trails for the Electronic Health Record (EHR) to determine when the 14:30 note was actually entered into the system.',
        'Deposition of the charge nurse regarding staffing ratios during the incident window.'
      ],
      confidenceScore: 92,
      sourceCitations: 14,
      legalPrecedents: 3
    },
    chatHistory: [
      {
        id: 'msg-1',
        sender: 'ai',
        time: '09:41 AM',
        content: 'I have indexed 12 documents for **Case #8821**, including the orthopedic surgery report from 03/12 and the follow-up physical therapy logs. \n\nYou can ask me to synthesize findings, identify inconsistencies, or locate specific clinical observations.'
      },
      {
        id: 'msg-2',
        sender: 'user',
        time: '09:42 AM',
        content: 'What does the surgeon note regarding the range of motion in the right knee post-operation?'
      },
      {
        id: 'msg-3',
        sender: 'ai',
        time: '09:42 AM',
        content: 'According to the **Operative Report (Ref: DOC-442)** by Dr. Aris, the passive range of motion immediately post-op was restricted to 15-45 degrees due to significant localized edema.',
        citation: {
          text: '"Patient exhibited guarded movement; knee flexion capped at 45° during initial table assessment."',
          source: 'Surgical_Report_Final.pdf',
          page: 4
        }
      }
    ]
  },
  {
    id: '9042',
    title: 'Estate of Miller - Probate Review',
    ref: '9042-AL',
    clientName: 'Alice Miller',
    clientAgeSex: '79-year-old female',
    primaryDiagnosis: ['Cognitive Dementia', 'Osteoarthritis'],
    status: 'PROCESSING',
    dateCreated: 'Oct 24, 2023',
    documents: [
      {
        id: 'doc-9042-1',
        name: 'Neurology_Intake_Form.pdf',
        uuid: '9042-NEU-001',
        size: '1.8 MB',
        uploadedAt: 'Jan 13, 2024',
        status: 'PROCESSED'
      }
    ],
    chatHistory: []
  },
  {
    id: '7719',
    title: 'Thompson Cardiology Malpractice',
    ref: '7719-MK',
    clientName: 'Michael Thompson',
    clientAgeSex: '45-year-old male',
    primaryDiagnosis: ['Myocardial Infarction', 'Coronary Artery Disease'],
    status: 'COMPLETED',
    dateCreated: 'Oct 23, 2023',
    documents: [
      {
        id: 'doc-7719-1',
        name: 'EKG_Strip_Log_02.pdf',
        uuid: '7719-CAR-011',
        size: '3.1 MB',
        uploadedAt: 'Jan 10, 2024',
        status: 'PROCESSED'
      }
    ],
    chatHistory: []
  },
  {
    id: '8112',
    title: 'Rivera vs. Health Systems Inc.',
    ref: '8112-RT',
    clientName: 'Rosa Rivera',
    clientAgeSex: '62-year-old female',
    primaryDiagnosis: ['Post-Op Infection', 'Sepsis'],
    status: 'FAILED',
    dateCreated: 'Oct 22, 2023',
    documents: [
      {
        id: 'doc-8112-1',
        name: 'Lab_Report_Pathology.pdf',
        uuid: '8112-LAB-042',
        size: '1.4 MB',
        uploadedAt: 'Jan 08, 2024',
        status: 'FAILED'
      }
    ],
    chatHistory: []
  },
  {
    id: '9201',
    title: 'Davis Oncology Report Summary',
    ref: '9201-PP',
    clientName: 'Howard Davis',
    clientAgeSex: '67-year-old male',
    primaryDiagnosis: ['Stage II Lung Adenocarcinoma'],
    status: 'COMPLETED',
    dateCreated: 'Oct 22, 2023',
    documents: [],
    chatHistory: []
  },
  {
    id: '6610',
    title: 'Surgical Audit: Case 2023-9',
    ref: '6610-AS',
    clientName: 'Audit File #9',
    clientAgeSex: 'N/A',
    primaryDiagnosis: ['Pre-operative Checklist Audit'],
    status: 'COMPLETED',
    dateCreated: 'Oct 21, 2023',
    documents: [],
    chatHistory: []
  }
];
