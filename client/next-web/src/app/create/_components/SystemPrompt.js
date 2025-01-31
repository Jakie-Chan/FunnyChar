import {
  Textarea,
  Button
} from '@nextui-org/react';
import { useAppStore } from '@/zustand/store';

export default function SystemPrompt() {
  const {
    formData,
    setFormData,
    autoGenerate,
  } = useAppStore();

  return (
    <div className="flex flex-col gap-3">
      <h4 className="font-medium text-lg">System Prompt(required)</h4>
      {/* <p className="text-small">You can auto-generate the prompt based on character name and background</p> */}
      <div className="flex flex-col w-fit">
        {/* <Button
          onPress={autoGenerate}
          isLoading={formData.system_prompt === 'Generating...'}
          className="bg-real-contrastBlue"
        >
          Auto generate
        </Button> */}
        {/* <span className="text-tiny text-warning">* It may take ~1 minute</span> */}
      </div>
      <Textarea
        label=""
        labelPlacement="outside"
        placeholder="Write your own prompt"
        classNames={{
          label: 'text-lg',
          inputWrapper: [
            'bg-white/10',
            'data-[hover=true]:bg-white/10',
            'group-data-[focus=true]:bg-white/10'
          ],
          input: 'text-base',
        }}
        value={formData.system_prompt}
        onValueChange={(value) =>
          setFormData({
            system_prompt: value
          })
        }
      />
    </div>
  );
}
