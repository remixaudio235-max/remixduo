// Additive Duo MAC profile; existing WIN fpv2/fpv3 behavior is preserved.
export function validateClientProfile(platform: string, fpv: number, ids: string[]) {
  if (platform === 'MAC') {
    if (fpv !== 4 || ids.length < 1 || ids.length > 2 ||
        ids.some(id => !/^DUOM4-[0-9A-F]{64}$/.test(id))) {
      throw new Error('MAC yêu cầu FPV4 và Machine ID DUOM4 hợp lệ.');
    }
  } else if (fpv === 4 || ids.some(id => id.startsWith('DUOM4-'))) {
    throw new Error('FPV4 chỉ dành cho Duo MAC.');
  }
}

export function clientProfileMismatch(license: {platform?: string; fpv?: number}, machine: string): boolean {
  if (machine.startsWith('DUOM4-') || license.platform === 'MAC') {
    return license.platform !== 'MAC' || Number(license.fpv) !== 4 ||
           !/^DUOM4-[0-9A-F]{64}$/.test(machine);
  }
  return false;
}

export function macMachineAuthorized(license: {platform?: string; hw_ids_json?: string}, machine: string): boolean {
  if (license.platform !== 'MAC') return true; // Preserve the existing WIN lifecycle.
  try {
    const ids=JSON.parse(license.hw_ids_json || '[]');
    return Array.isArray(ids) && ids.includes(machine);
  } catch { return false; }
}
