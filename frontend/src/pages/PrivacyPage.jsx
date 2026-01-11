import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../components/AuthProvider';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function PrivacyPage() {
  const { token } = useAuth();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchSettings();
  }, [token]);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/v1/privacy/settings`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSettings(response.data);
    } catch (error) {
      console.error('Failed to fetch privacy settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage('');
      
      await axios.post(
        `${API_BASE_URL}/api/v1/privacy/settings`,
        {
          data_retention_mode: settings.data_retention_mode,
          log_usage: settings.privacy_settings.log_usage,
          log_inputs: settings.privacy_settings.log_inputs,
          log_outputs: settings.privacy_settings.log_outputs
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setMessage('Privacy settings updated successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('Failed to update settings: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  const updateSetting = (key, value) => {
    if (key === 'data_retention_mode') {
      setSettings({ ...settings, data_retention_mode: value });
    } else {
      setSettings({
        ...settings,
        privacy_settings: { ...settings.privacy_settings, [key]: value }
      });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen gradient-bg text-white flex items-center justify-center">
        <p>Loading privacy settings...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg text-white">
      <div className="container mx-auto px-6 py-12 max-w-4xl">
        <header className="mb-8">
          <h1 className="text-4xl font-bold gradient-text">Privacy by Design</h1>
          <p className="text-gray-300 mt-2">Enterprise-grade data controls - You own your data</p>
        </header>

        {message && (
          <div className={`mb-6 p-4 rounded-lg ${message.includes('success') ? 'bg-green-500/20 border border-green-500/50' : 'bg-red-500/20 border border-red-500/50'}`}>
            {message}
          </div>
        )}

        {/* Data Retention Mode */}
        <div className="card mb-6">
          <h2 className="text-xl font-semibold mb-4">🔒 Data Retention Mode</h2>
          <p className="text-gray-300 mb-4">
            Control how Nexus Releval handles your data. Choose the level of privacy that matches your compliance requirements.
          </p>
          
          <div className="space-y-3">
            <label className="flex items-start gap-3 p-4 border border-brand-purple/30 rounded-lg hover:bg-brand-purple/5 cursor-pointer">
              <input
                type="radio"
                name="retention"
                value="standard"
                checked={settings?.data_retention_mode === 'standard'}
                onChange={(e) => updateSetting('data_retention_mode', e.target.value)}
                className="mt-1"
              />
              <div>
                <div className="font-semibold">Standard Mode</div>
                <div className="text-sm text-gray-400">
                  Logs usage metadata (request counts, tokens, costs) for billing and analytics. 
                  No conversation content is stored.
                </div>
              </div>
            </label>

            <label className="flex items-start gap-3 p-4 border-2 border-purple-500 rounded-lg hover:bg-purple-500/10 cursor-pointer">
              <input
                type="radio"
                name="retention"
                value="zero-retention"
                checked={settings?.data_retention_mode === 'zero-retention'}
                onChange={(e) => updateSetting('data_retention_mode', e.target.value)}
                className="mt-1"
              />
              <div>
                <div className="font-semibold flex items-center gap-2">
                  Zero-Data-Retention (ZDR) <span className="text-xs bg-purple-500 px-2 py-1 rounded">ENTERPRISE</span>
                </div>
                <div className="text-sm text-gray-400">
                  Data exists only in volatile memory. Once the response is sent, it's permanently deleted. 
                  Nothing to subpoena, nothing to hack. GDPR/HIPAA compliant.
                </div>
              </div>
            </label>

            <label className="flex items-start gap-3 p-4 border border-brand-purple/30 rounded-lg hover:bg-brand-purple/5 cursor-pointer">
              <input
                type="radio"
                name="retention"
                value="anonymous"
                checked={settings?.data_retention_mode === 'anonymous'}
                onChange={(e) => updateSetting('data_retention_mode', e.target.value)}
                className="mt-1"
              />
              <div>
                <div className="font-semibold">Anonymous Mode</div>
                <div className="text-sm text-gray-400">
                  Logs aggregate statistics without linking to your account. 
                  Maximum privacy while supporting system improvements.
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Granular Logging Controls */}
        <div className="card mb-6">
          <h2 className="text-xl font-semibold mb-4">📊 Logging Controls</h2>
          <p className="text-gray-300 mb-4">
            Fine-tune what gets logged. All settings respect your data retention mode.
          </p>

          <div className="space-y-4">
            <label className="flex items-center justify-between p-4 bg-brand-darker rounded-lg">
              <div>
                <div className="font-semibold">Log Usage Metadata</div>
                <div className="text-sm text-gray-400">Request counts, tokens processed, estimated costs</div>
              </div>
              <input
                type="checkbox"
                checked={settings?.privacy_settings?.log_usage ?? true}
                onChange={(e) => updateSetting('log_usage', e.target.checked)}
                className="w-5 h-5"
              />
            </label>

            <label className="flex items-center justify-between p-4 bg-brand-darker rounded-lg">
              <div>
                <div className="font-semibold">Log Input Text</div>
                <div className="text-sm text-gray-400">Store user questions/prompts (not recommended for sensitive data)</div>
              </div>
              <input
                type="checkbox"
                checked={settings?.privacy_settings?.log_inputs ?? false}
                onChange={(e) => updateSetting('log_inputs', e.target.checked)}
                className="w-5 h-5"
              />
            </label>

            <label className="flex items-center justify-between p-4 bg-brand-darker rounded-lg">
              <div>
                <div className="font-semibold">Log Output Text</div>
                <div className="text-sm text-gray-400">Store AI responses (not recommended for HIPAA/GDPR compliance)</div>
              </div>
              <input
                type="checkbox"
                checked={settings?.privacy_settings?.log_outputs ?? false}
                onChange={(e) => updateSetting('log_outputs', e.target.checked)}
                className="w-5 h-5"
              />
            </label>
          </div>
        </div>

        {/* Compliance Info */}
        <div className="card bg-green-500/10 border border-green-500/30 mb-6">
          <h2 className="text-xl font-semibold mb-3">✅ Compliance Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-3 bg-brand-darker rounded">
              <div className="text-2xl mb-1">🇪🇺</div>
              <div className="font-semibold">GDPR Ready</div>
              <div className="text-xs text-gray-400">European data protection</div>
            </div>
            <div className="text-center p-3 bg-brand-darker rounded">
              <div className="text-2xl mb-1">🏥</div>
              <div className="font-semibold">HIPAA Compatible</div>
              <div className="text-xs text-gray-400">Healthcare privacy</div>
            </div>
            <div className="text-center p-3 bg-brand-darker rounded">
              <div className="text-2xl mb-1">🔒</div>
              <div className="font-semibold">SOC 2 Type II</div>
              <div className="text-xs text-gray-400">Security controls</div>
            </div>
          </div>
        </div>

        {/* On-Premise Option */}
        <div className="card bg-blue-500/10 border border-blue-500/30">
          <h2 className="text-xl font-semibold mb-3">🏢 On-Premise Deployment</h2>
          <p className="text-gray-300 mb-4">
            Enterprise customers can run Nexus Releval entirely on their own infrastructure. 
            Your data never leaves your firewall.
          </p>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-gray-400">Interested in on-premise?</span>
            <a href="mailto:enterprise@nexusreleval.com" className="btn-primary py-2 px-4">
              Contact Sales
            </a>
          </div>
        </div>

        {/* Save Button */}
        <div className="mt-8 flex items-center justify-between">
          <p className="text-gray-400 text-sm">Changes take effect immediately</p>
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary py-3 px-8 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Privacy Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}
