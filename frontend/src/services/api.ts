import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  AuthResponse,
  Assessment,
  AssessmentListItem,
  ExtractedData,
  QualitativeResponse,
  RiskAssessment,
  Recommendation,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || '/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle auth errors
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async register(email: string, password: string, fullName: string): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    return response.data;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await this.client.post<AuthResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  }

  async getCurrentUser(): Promise<AuthResponse['user']> {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  // Assessments
  async createAssessment(vendorName: string, registrationNumber?: string): Promise<Assessment> {
    const response = await this.client.post<Assessment>('/assessments', {
      vendor_name: vendorName,
      vendor_registration_number: registrationNumber,
    });
    return response.data;
  }

  async listAssessments(): Promise<AssessmentListItem[]> {
    const response = await this.client.get<AssessmentListItem[]>('/assessments');
    return response.data;
  }

  async getAssessment(id: number): Promise<Assessment> {
    const response = await this.client.get<Assessment>(`/assessments/${id}`);
    return response.data;
  }

  async updateAssessment(id: number, data: Partial<Assessment>): Promise<Assessment> {
    const response = await this.client.patch<Assessment>(`/assessments/${id}`, data);
    return response.data;
  }

  async deleteAssessment(id: number): Promise<void> {
    await this.client.delete(`/assessments/${id}`);
  }

  // File Upload
  async uploadFile(assessmentId: number, file: File): Promise<{ statement_id: number; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post(`/assessments/${assessmentId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async triggerExtraction(assessmentId: number): Promise<{ message: string }> {
    const response = await this.client.post(`/assessments/${assessmentId}/extract`);
    return response.data;
  }

  async getExtractionStatus(assessmentId: number): Promise<{
    total_files: number;
    processed_files: number;
    is_complete: boolean;
    has_errors: boolean;
    extracted_years: number;
    status: 'pending' | 'processing' | 'complete';
  }> {
    const response = await this.client.get(`/assessments/${assessmentId}/extraction-status`);
    return response.data;
  }

  // Financial Data
  async createFinancialData(
    assessmentId: number,
    data: Partial<ExtractedData> & { fiscal_year: number }
  ): Promise<ExtractedData> {
    const response = await this.client.post<ExtractedData>(
      `/assessments/${assessmentId}/financial-data`,
      data
    );
    return response.data;
  }

  async updateFinancialData(
    assessmentId: number,
    dataId: number,
    data: Partial<ExtractedData>
  ): Promise<ExtractedData> {
    const response = await this.client.put<ExtractedData>(
      `/assessments/${assessmentId}/financial-data/${dataId}`,
      data
    );
    return response.data;
  }

  async deleteFinancialData(assessmentId: number, dataId: number): Promise<void> {
    await this.client.delete(`/assessments/${assessmentId}/financial-data/${dataId}`);
  }

  async confirmFinancialData(assessmentId: number): Promise<{ message: string; current_step: number }> {
    const response = await this.client.post(`/assessments/${assessmentId}/confirm-data`);
    return response.data;
  }

  // Qualitative Responses
  async updateQualitativeResponse(
    assessmentId: number,
    questionId: string,
    data: { response?: string; notes?: string }
  ): Promise<QualitativeResponse> {
    const response = await this.client.put<QualitativeResponse>(
      `/assessments/${assessmentId}/qualitative/${questionId}`,
      data
    );
    return response.data;
  }

  // Risk Assessment
  async calculateRatios(assessmentId: number): Promise<RiskAssessment> {
    const response = await this.client.post<RiskAssessment>(`/assessments/${assessmentId}/calculate`);
    return response.data;
  }

  // Recommendation
  async generateRecommendation(assessmentId: number): Promise<Recommendation> {
    const response = await this.client.post<Recommendation>(`/assessments/${assessmentId}/recommend`);
    return response.data;
  }

  async signOff(assessmentId: number): Promise<{ message: string; signed_off_at: string }> {
    const response = await this.client.post(`/assessments/${assessmentId}/sign-off`);
    return response.data;
  }

  async downloadPdf(assessmentId: number): Promise<Blob> {
    const response = await this.client.get(`/assessments/${assessmentId}/download-pdf`, {
      responseType: 'blob'
    });
    return response.data;
  }

  async downloadExcel(assessmentId: number): Promise<Blob> {
    const response = await this.client.get(`/assessments/${assessmentId}/download-excel`, {
      responseType: 'blob'
    });
    return response.data;
  }
}

export const api = new ApiService();
