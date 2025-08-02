import React, { useEffect, useState } from 'react';
import { PatientType } from '../types';
import EmailInput from './EmailInput';
import PhoneInput from './PhoneInput';

interface PatientFormModalProps {
  patient?: PatientType | null;
  onSubmit: (data: any) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function PatientFormModal({
  patient,
  onSubmit,
  onCancel,
  isLoading = false,
}: PatientFormModalProps) {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    date_of_birth: '',
    sex: '',
    phone: '',
    email: '',
    location: ['', '', '', ''], // [city, state, country, zipcode]
  });

  const [error, setError] = useState('');

  useEffect(() => {
    if (patient) {
      setFormData({
        first_name: patient.first_name || '',
        last_name: patient.last_name || '',
        date_of_birth: patient.date_of_birth
          ? patient.date_of_birth.split('T')[0]
          : '',
        sex: patient.sex || '',
        phone: patient.phone || '',
        email: patient.email || '',
        location: patient.location || ['', '', '', ''],
      });
    }
  }, [patient]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ): void => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleLocationChange = (index: number, value: string): void => {
    setFormData(prev => ({
      ...prev,
      location: prev.location.map((item, i) => (i === index ? value : item)),
    }));
  };

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    setError('');

    try {
      onSubmit(formData);
    } catch (err) {
      if (
        typeof err === 'object' &&
        err !== null &&
        'response' in err &&
        typeof (err as any).response === 'object'
      ) {
        setError((err as any).response?.data?.error || 'An error occurred');
      } else {
        setError('An error occurred');
      }
      console.error(err);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-6">
        {patient ? 'Edit Patient' : 'Add New Patient'}
      </h2>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              First Name *
            </label>
            <input
              type="text"
              name="first_name"
              value={formData.first_name}
              onChange={handleInputChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Last Name *
            </label>
            <input
              type="text"
              name="last_name"
              value={formData.last_name}
              onChange={handleInputChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Date of Birth
            </label>
            <input
              type="date"
              name="date_of_birth"
              value={formData.date_of_birth}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Sex</label>
            <select
              name="sex"
              value={formData.sex}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select...</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="O">Other</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <PhoneInput
            value={formData.phone}
            onChange={(value) => setFormData(prev => ({ ...prev, phone: value }))}
            label="Phone"
            placeholder="Enter phone number"
          />

          <EmailInput
            value={formData.email}
            onChange={(value) => setFormData(prev => ({ ...prev, email: value }))}
            label="Email"
            placeholder="Enter email address"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Address</label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              placeholder="City"
              value={formData.location[0]}
              onChange={e => handleLocationChange(0, e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="text"
              placeholder="State/Province"
              value={formData.location[1]}
              onChange={e => handleLocationChange(1, e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="text"
              placeholder="Country"
              value={formData.location[2]}
              onChange={e => handleLocationChange(2, e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="text"
              placeholder="Postal Code"
              value={formData.location[3]}
              onChange={e => handleLocationChange(3, e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex justify-end space-x-4">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
          >
            {isLoading
              ? 'Saving...'
              : patient
                ? 'Update Patient'
                : 'Create Patient'}
          </button>
        </div>
      </form>
    </div>
  );
}
