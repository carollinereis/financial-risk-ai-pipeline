import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchCustomers = async () => {
  const response = await api.get('/customers');
  return response.data;
};

export const fetchCustomerProfile = async (customerId) => {
  const response = await api.get(`/customers/${customerId}`);
  return response.data;
};

export const runRiskAudit = async (customerId) => {
  const response = await api.post(`/customers/${customerId}/audit`);
  return response.data;
};