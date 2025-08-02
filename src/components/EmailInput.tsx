import React, { useState } from 'react';

interface EmailInputProps {
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  label?: string;
  placeholder?: string;
  className?: string;
}

const EmailInput: React.FC<EmailInputProps> = ({
  value,
  onChange,
  required = false,
  label = "Email",
  placeholder = "Enter email address",
  className = ""
}) => {
  const [error, setError] = useState<string>('');
  const [touched, setTouched] = useState<boolean>(false);

  const validateEmail = (email: string): string => {
    if (required && !email.trim()) {
      return 'Email is required';
    }
    if (email.trim() && !/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)) {
      return 'Invalid email format';
    }
    return '';
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    
    if (touched) {
      const validationError = validateEmail(newValue);
      setError(validationError);
    }
  };

  const handleBlur = () => {
    setTouched(true);
    const validationError = validateEmail(value);
    console.log('Validation error:', validationError); 
    setError(validationError);
  };

  const hasError = error && touched;

  return (
    <div className={className}>
      <label className="block text-sm font-medium mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type="email"
        value={value}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder={placeholder}
        className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          hasError 
            ? 'border-red-500 focus:ring-red-500' 
            : 'border-gray-300'
        }`}
      />
      {hasError && (
        <p className="text-red-500 text-sm mt-1">{error}</p>
      )}
    </div>
  );
};

export default EmailInput;