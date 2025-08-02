import React, { useState } from 'react';

interface PhoneInputProps {
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  label?: string;
  placeholder?: string;
  className?: string;
  countryCode?: string; 
  showFormatHint?: boolean; 
}

const PhoneInput: React.FC<PhoneInputProps> = ({
  value,
  onChange,
  required = false,
  label = "Phone",
  placeholder = "Enter phone number",
  className = "",
  countryCode = "1",
  showFormatHint = false 
}) => {
  const [error, setError] = useState<string>('');
  const [touched, setTouched] = useState<boolean>(false);


  const getCountryInfo = (code: string) => {
    const countryMap: { [key: string]: { name: string; format: string; minLength: number; maxLength: number } } = {
      "1": { name: "US/Canada", format: "(XXX) XXX-XXXX", minLength: 10, maxLength: 10 },
      "44": { name: "UK", format: "+44 XXXX XXX XXXX", minLength: 10, maxLength: 11 },
      "33": { name: "France", format: "+33 X XX XX XX XX", minLength: 9, maxLength: 9 },
      "49": { name: "Germany", format: "+49 XXX XXXXXXXX", minLength: 10, maxLength: 12 },
      "61": { name: "Australia", format: "+61 X XXXX XXXX", minLength: 9, maxLength: 9 },
      "91": { name: "India", format: "+91 XXXXX XXXXX", minLength: 10, maxLength: 10 },
    };
    
    return countryMap[code] || { name: "International", format: `+${code} XXXXXXXXXX`, minLength: 7, maxLength: 15 };
  };

  const validatePhone = (phone: string): string => {
    if (required && !phone.trim()) {
      return 'Phone number is required';
    }
    
    if (!phone.trim()) return '';

    
    const digitsOnly = phone.replace(/\D/g, '');
    const countryInfo = getCountryInfo(countryCode);
    
    
    if (countryCode === "1") {
      if (digitsOnly.length > 0 && digitsOnly.length < countryInfo.minLength) {
        return `Phone number must be ${countryInfo.minLength} digits`;
      }
      if (digitsOnly.length > countryInfo.maxLength) {
        return 'Phone number is too long';
      }
    } else {
      if (digitsOnly.length > 0 && digitsOnly.length < (countryCode.length + countryInfo.minLength)) {
        return `Phone number must be at least ${countryInfo.minLength} digits`;
      }
      if (digitsOnly.length > (countryCode.length + countryInfo.maxLength)) {
        return 'Phone number is too long';
      }
    }
    
    return '';
  };

  const formatPhone = (value: string, isDeleting: boolean = false): string => {
    const digitsOnly = value.replace(/\D/g, '');
    
    if (countryCode === "1") {
      if (isDeleting) {
        if (digitsOnly.length === 0) return '';
        if (digitsOnly.length <= 3) return digitsOnly;
        if (digitsOnly.length <= 6) return `(${digitsOnly.substring(0, 3)}) ${digitsOnly.substring(3)}`;
        return `(${digitsOnly.substring(0, 3)}) ${digitsOnly.substring(3, 6)}-${digitsOnly.substring(6, 10)}`;
      } else {
        if (digitsOnly.length >= 10) {
          return digitsOnly.substring(0, 10).replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
        } else if (digitsOnly.length >= 6) {
          return digitsOnly.replace(/(\d{3})(\d{3})/, '($1) $2-');
        } else if (digitsOnly.length >= 3) {
          return digitsOnly.replace(/(\d{3})/, '($1) ');
        }
        return digitsOnly;
      }
    } else {
      if (digitsOnly.length > countryCode.length) {
        const numberPart = digitsOnly.substring(countryCode.length);
        if (countryCode === "44" && numberPart.length >= 7) {
          return `+${countryCode} ${numberPart.substring(0, 2)} ${numberPart.substring(2, 6)} ${numberPart.substring(6, 10)}`;
        } else {
          return `+${countryCode} ${numberPart.match(/.{1,4}/g)?.join(' ') || numberPart}`;
        }
      } else if (digitsOnly.length > 0) {
        return `+${digitsOnly}`;
      }
      return digitsOnly;
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    const allowedChars = /^[\d\s\(\)\-\+]*$/;
    if (!allowedChars.test(inputValue)) {
      return; 
    }

    const isDeleting = inputValue.length < value.length;

    const digitsOnly = inputValue.replace(/\D/g, '');

    const formattedValue = formatPhone(digitsOnly, isDeleting);
    onChange(formattedValue);
    
    if (touched) {
      const validationError = validatePhone(formattedValue);
      setError(validationError);
    }
  };

  const handleBlur = () => {
    setTouched(true);
    const validationError = validatePhone(value);
    setError(validationError);
  };

  const hasError = error && touched;
  const countryInfo = getCountryInfo(countryCode);

  return (
    <div className={className}>
      <label className="block text-sm font-medium mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type="tel"
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
      {showFormatHint && (
        <p className="text-gray-500 text-xs mt-1">
          Format: {countryInfo.format} ({countryInfo.name})
        </p>
      )}
    </div>
  );
};

export default PhoneInput;