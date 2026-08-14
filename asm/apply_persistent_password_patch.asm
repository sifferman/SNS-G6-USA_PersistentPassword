; Derivation of every address used here: docs/reverse_engineering_notes.md
; The memory map include is generated into build/ from
; python/goof_troop_usa/memory_map.py before every assembly

lorom

incsrc "goof_troop_usa_memory_map.asm"

!BLOCK_MOVE_LENGTH_FOR_SETTINGS_BLOCK            = !SETTINGS_BLOCK_SIZE_IN_BYTES-1
!SOUND_DRIVER_UPLOADED_FLAG_WITHIN_WORK_RAM_BANK = !SOUND_DRIVER_UPLOADED_FLAG_IN_WORK_RAM&$FFFF


org !CARTRIDGE_TYPE_HEADER_FIELD
    db !CARTRIDGE_TYPE_ROM_WITH_BATTERY_BACKED_SAVE_RAM

org !ROM_SIZE_HEADER_FIELD
    db !ROM_SIZE_1024_KILOBYTES

org !SAVE_RAM_SIZE_HEADER_FIELD
    db !SAVE_RAM_SIZE_TWO_KILOBYTES


org !SAVE_RAM_DETECTION_ROUTINE_FIRST_ADDRESS

RestoreSettingsFromSaveRamOnBoot:
    REP #$30
    LDX.w #!SETTINGS_BLOCK_IN_SAVE_RAM
    LDY.w #!SETTINGS_BLOCK_IN_WORK_RAM
    LDA.w #!BLOCK_MOVE_LENGTH_FOR_SETTINGS_BLOCK
    MVN !SETTINGS_BLOCK_IN_WORK_RAM>>16, !SETTINGS_BLOCK_IN_SAVE_RAM>>16
    SEP #$20
    STZ.w !SOUND_DRIVER_UPLOADED_FLAG_WITHIN_WORK_RAM_BANK
    SEP #$30
    RTS

fillbyte $EA
fill !SAVE_RAM_DETECTION_ROUTINE_LAST_ADDRESS-pc()+1

assert pc() == !SAVE_RAM_DETECTION_ROUTINE_LAST_ADDRESS+1, "the save RAM detection routine must be overwritten in full, so that none of its instructions survive"


org !PATCH_CODE_BANK_ADDRESS

PreserveVanillaJumpIntoTheAddedBank:
    JML !RESET_ENTRY_POINT

assert PreserveVanillaJumpIntoTheAddedBank == !PATCH_CODE_BANK_ADDRESS, "vanilla jumps into the first address of the added bank, so this trampoline must stay first in it or that jump lands inside another routine"

CopySettingsBlockToSaveRam:
    PHB
    PHP
    REP #$30
    LDX.w #!SETTINGS_BLOCK_IN_WORK_RAM
    LDY.w #!SETTINGS_BLOCK_IN_SAVE_RAM
    LDA.w #!BLOCK_MOVE_LENGTH_FOR_SETTINGS_BLOCK
    MVN !SETTINGS_BLOCK_IN_SAVE_RAM>>16, !SETTINGS_BLOCK_IN_WORK_RAM>>16
    PLP
    PLB
    RTL

RecordFurthestLevelReachedToSaveRam:
    STA.l !FURTHEST_LEVEL_REACHED_IN_WORK_RAM
    JML CopySettingsBlockToSaveRam

SaveSettingsThenReloadThem:
    JSL CopySettingsBlockToSaveRam
    JML !RELOAD_SETTINGS_ROUTINE


org !LAST_ADDRESS_OF_EXPANDED_ROM
    db $00


org !STORE_FURTHEST_LEVEL_REACHED_ON_LEVEL_CLEARED
    JSL RecordFurthestLevelReachedToSaveRam

org !STORE_FURTHEST_LEVEL_REACHED_ON_PASSWORD_ACCEPTED
    JSL RecordFurthestLevelReachedToSaveRam

org !RELOAD_SETTINGS_CALL_AFTER_OPTION_04
    JSL SaveSettingsThenReloadThem

org !RELOAD_SETTINGS_CALL_AFTER_SOUND_OPTION
    JSL SaveSettingsThenReloadThem

org !RELOAD_SETTINGS_CALL_AFTER_PLAYER_ONE_THROW_TYPE
    JSL SaveSettingsThenReloadThem

org !RELOAD_SETTINGS_CALL_AFTER_OPTION_06
    JSL SaveSettingsThenReloadThem

org !RELOAD_SETTINGS_CALL_AFTER_OPTION_07
    JSL SaveSettingsThenReloadThem
