# ErrorModal Component

A reusable React component for displaying error messages with customizable actions.

## Features

- **Customizable Error Messages**: Set custom error titles and descriptions
- **Suggested Actions**: Provide actionable buttons (Login, Sign Up, Home, etc.)
- **Responsive Design**: Works on desktop and mobile devices
- **Accessibility**: Includes proper ARIA labels and keyboard navigation
- **Smooth Animations**: CSS animations for better user experience

## Basic Usage

```tsx
import ErrorModal from './components/ErrorModal';

function MyComponent() {
  const [errorModal, setErrorModal] = useState({
    isOpen: false,
    error: 'Something went wrong',
    description: 'An error occurred',
  });

  const handleClose = () => {
    setErrorModal(prev => ({ ...prev, isOpen: false }));
  };

  return (
    <div>
      <ErrorModal
        isOpen={errorModal.isOpen}
        error={errorModal.error}
        description={errorModal.description}
        onClose={handleClose}
      />
    </div>
  );
}
```

## Using the useErrorModal Hook

For easier error handling, use the `useErrorModal` hook:

```tsx
import { useErrorModal } from '../hooks/useErrorModal';
import ErrorModal from '../components/ErrorModal';

function MyComponent() {
  const { errorModal, showError, hideError, showNetworkError } = useErrorModal();

  const handleApiCall = async () => {
    try {
      const response = await fetch('/api/data');
      if (!response.ok) {
        showError('API Error', 'Failed to fetch data', 'home');
      }
    } catch (error) {
      showNetworkError();
    }
  };

  return (
    <div>
      <ErrorModal
        isOpen={errorModal.isOpen}
        error={errorModal.error}
        description={errorModal.description}
        suggested_action={errorModal.suggested_action}
        onClose={hideError}
      />
    </div>
  );
}
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `error` | string | "Something went wrong" | The error title displayed at the top |
| `description` | string | "An unknown error has occurred..." | The error description/body text |
| `suggested_action` | string | undefined | Action to perform (login, register, home) |
| `isOpen` | boolean | false | Whether the modal is visible |
| `onClose` | function | required | Function called when modal is closed |

## Suggested Actions

The component supports the following suggested actions:

- **`login`**: Shows "Login" button and opens the login modal
- **`register`**: Shows "Sign Up" button and opens the register modal  
- **`home`**: Shows "Home" button and navigates to the home page
- **`undefined`**: No action button is shown, only "Dismiss"

## Utility Functions

### createErrorModalState

Creates the state object for the error modal:

```tsx
import { createErrorModalState } from './components/ErrorModal';

const errorState = createErrorModalState(
  'Network Error',
  'Unable to connect to server',
  'home'
);
```

### useErrorModal Hook Methods

- `showError(error, description, suggested_action?)`: Show a custom error
- `showNetworkError()`: Show a network connection error
- `showAuthError(description)`: Show an authentication error
- `showPermissionError()`: Show a permission denied error
- `hideError()`: Hide the error modal

## Styling

The component uses CSS classes that can be customized:

- `.error-modal-overlay`: The backdrop overlay
- `.error-modal`: The modal container
- `.error-modal-header`: Header section with title and close button
- `.error-modal-title`: Error title styling
- `.error-modal-close`: Close button styling
- `.error-modal-body`: Body section with description
- `.error-modal-footer`: Footer section with action buttons
- `.error-modal-action-button`: Primary action button
- `.error-modal-dismiss-button`: Dismiss button

## Examples

### Authentication Error
```tsx
showError(
  'Authentication Failed',
  'Your session has expired. Please log in again.',
  'login'
);
```

### Permission Error
```tsx
showError(
  'Access Denied',
  'You do not have permission to view this resource.',
  'home'
);
```

### Network Error
```tsx
showNetworkError();
```

### Custom Error with No Action
```tsx
showError(
  'Validation Error',
  'Please check your input and try again.'
  // No suggested_action - only shows Dismiss button
);
``` 