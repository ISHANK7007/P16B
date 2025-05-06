// Pseudocode for profile definition system
interface AgentProfile {
  id: string;
  extends: string[] | null;  // Parent profiles to inherit from
  
  baseCharacteristics: {
    expertise: string[];
    tone: string[];
    constraints: string[];
  };
  
  templateDefaults: Record<string, TemplateConfig>;
  
  inferenceParams: {
    temperature: number;
    topP: number;
    frequencyPenalty: number;
    // Other inference settings
  };
  
  outputFormats: Record<string, OutputSchema>;
  
  evaluationCriteria: Record<string, ValidationRule[]>;
  
  // Method to check if a property is explicitly overridden
  hasExplicitOverride(propertyPath: string): boolean;
}

class ProfileRegistry {
  // Resolves a complete profile with all inherited properties
  resolveProfile(profileId: string, taskContext?: TaskContext): ResolvedProfile {
    // Implementation of inheritance resolution
  }
  
  // Allows composing multiple profiles for specific use cases
  composeProfiles(profileIds: string[], overrides?: PartialProfile): ResolvedProfile {
    // Implementation of composition logic
  }
}