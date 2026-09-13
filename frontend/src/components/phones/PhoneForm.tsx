/**
 * Phone form component for create/edit
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreatePhone, useUpdatePhone } from '../../hooks/usePhones';
import type { Phone } from '../../api/types';

const phoneSchema = z.object({
  mac: z.string().min(1, 'MAC address is required'),
  model: z.string().min(1, 'Model is required'),
  extension: z.string().min(1, 'Extension is required'),
  display_name: z.string().optional(),
  password: z.string().min(1, 'Password is required'),
  pbx_server: z.string().optional(),
  pbx_port: z.number().optional().nullable(),
  transport: z.string().optional(),
  label: z.string().optional(),
  codecs: z.string().optional(), // Will be split into array on submit
});

type PhoneFormData = z.infer<typeof phoneSchema>;

interface PhoneFormProps {
  phone: Phone | null;
  onClose: () => void;
}

export default function PhoneForm({ phone, onClose }: PhoneFormProps) {
  const isEditing = !!phone;
  const createPhone = useCreatePhone();
  const updatePhone = useUpdatePhone(phone?.mac || '');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PhoneFormData>({
    resolver: zodResolver(phoneSchema),
    defaultValues: phone
      ? {
          mac: phone.mac,
          model: phone.model,
          extension: phone.extension,
          display_name: phone.display_name || '',
          password: '', // Don't populate password for security
          pbx_server: phone.pbx_server || '',
          pbx_port: phone.pbx_port || undefined,
          transport: phone.transport || '',
          label: phone.label || '',
          codecs: phone.codecs ? phone.codecs.join(',') : '',
        }
      : undefined,
  });

  const onSubmit = async (data: PhoneFormData) => {
    try {
      // Convert codecs string to array
      const codecsArray = data.codecs
        ? data.codecs.split(',').map((c) => c.trim()).filter(Boolean)
        : null;

      if (isEditing) {
        // For update, only send changed fields
        const updates: any = {};
        if (data.model !== phone.model) updates.model = data.model;
        if (data.extension !== phone.extension) updates.extension = data.extension;
        if (data.display_name !== phone.display_name) updates.display_name = data.display_name;
        if (data.password) updates.password = data.password; // Only update if provided
        if (data.pbx_server !== phone.pbx_server) updates.pbx_server = data.pbx_server;
        if (data.pbx_port !== phone.pbx_port) updates.pbx_port = data.pbx_port;
        if (data.transport !== phone.transport) updates.transport = data.transport;
        if (data.label !== phone.label) updates.label = data.label;
        const phoneCodecsStr = phone.codecs ? phone.codecs.join(',') : '';
        if (data.codecs !== phoneCodecsStr) updates.codecs = codecsArray;

        await updatePhone.mutateAsync(updates);
      } else {
        await createPhone.mutateAsync({
          ...data,
          display_name: data.display_name || '',
          codecs: codecsArray,
        });
      }
      onClose();
    } catch (error) {
      alert(`Failed to ${isEditing ? 'update' : 'create'} phone: ${error}`);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            {isEditing ? 'Edit Phone' : 'Add New Phone'}
          </h3>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
          {/* MAC Address */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              MAC Address *
            </label>
            <input
              {...register('mac')}
              type="text"
              disabled={isEditing}
              placeholder="001122334455"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            {errors.mac && (
              <p className="mt-1 text-sm text-red-600">{errors.mac.message}</p>
            )}
          </div>

          {/* Extension */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Extension *
            </label>
            <input
              {...register('extension')}
              type="text"
              placeholder="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.extension && (
              <p className="mt-1 text-sm text-red-600">{errors.extension.message}</p>
            )}
          </div>

          {/* Display Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Display Name
            </label>
            <input
              {...register('display_name')}
              type="text"
              placeholder="John Doe"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Model */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Model *
            </label>
            <select
              {...register('model')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select model</option>
              <option value="yealink_t23g">Yealink T23G</option>
              <option value="fanvil_v64">Fanvil V64</option>
              <option value="grandstream_gds3710">Grandstream GDS3710 (Door Panel)</option>
            </select>
            {errors.model && (
              <p className="mt-1 text-sm text-red-600">{errors.model.message}</p>
            )}
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password {!isEditing && '*'}
            </label>
            <input
              {...register('password')}
              type="password"
              placeholder={isEditing ? 'Leave blank to keep current' : ''}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
            )}
            {isEditing && (
              <p className="mt-1 text-xs text-gray-500">
                Leave blank to keep the current password
              </p>
            )}
          </div>

          {/* Advanced Settings */}
          <details className="border border-gray-200 rounded-lg p-4">
            <summary className="cursor-pointer font-medium text-gray-700">
              Advanced Settings (Optional)
            </summary>
            <div className="mt-4 space-y-4">
              {/* PBX Server */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  PBX Server
                </label>
                <input
                  {...register('pbx_server')}
                  type="text"
                  placeholder="pbx.example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* PBX Port */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  PBX Port
                </label>
                <input
                  {...register('pbx_port', { valueAsNumber: true })}
                  type="number"
                  placeholder="5060"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Transport */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Transport
                </label>
                <select
                  {...register('transport')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Default</option>
                  <option value="udp">UDP</option>
                  <option value="tcp">TCP</option>
                  <option value="tls">TLS</option>
                </select>
              </div>

              {/* Codecs */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Codecs
                </label>
                <input
                  {...register('codecs')}
                  type="text"
                  placeholder="ulaw,alaw,g722"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Label */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Label
                </label>
                <input
                  {...register('label')}
                  type="text"
                  placeholder="Front Desk"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </details>

          {/* Form Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isSubmitting
                ? isEditing
                  ? 'Updating...'
                  : 'Creating...'
                : isEditing
                ? 'Update Phone'
                : 'Create Phone'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
