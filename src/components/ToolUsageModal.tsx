import React from 'react';
import './ToolUsageModal.css';

interface ToolUsageModalProps {
  isOpen: boolean;
  onClose: () => void;
  usedTools: string[];
}

const ToolUsageModal: React.FC<ToolUsageModalProps> = ({
  isOpen,
  onClose,
  usedTools,
}) => {
  if (!isOpen) return null;

  return (
    <div className="tool-usage-modal-overlay" onClick={onClose}>
      <div className="tool-usage-modal" onClick={e => e.stopPropagation()}>
        <div className="tool-usage-modal-header">
          <h3>Tools Used</h3>
          <button className="tool-usage-modal-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="tool-usage-modal-content">
          {usedTools.length > 0 ? (
            <ul className="tool-usage-list">
              {usedTools.map((tool, index) => (
                <li key={index} className="tool-usage-item">
                  {tool}
                </li>
              ))}
            </ul>
          ) : (
            <p className="no-tools-used">
              No tools were used in this response.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ToolUsageModal;
