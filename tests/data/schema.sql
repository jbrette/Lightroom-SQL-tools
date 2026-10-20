CREATE TABLE Adobe_AdditionalMetadata (
    id_local INTEGER PRIMARY KEY,
    id_global UNIQUE NOT NULL,
    additionalInfoSet INTEGER NOT NULL DEFAULT 0,
    embeddedXmp INTEGER NOT NULL DEFAULT 0,
    externalXmpIsDirty INTEGER NOT NULL DEFAULT 0,
    image INTEGER,
    incrementalWhiteBalance INTEGER NOT NULL DEFAULT 0,
    internalXmpDigest,
    isRawFile INTEGER NOT NULL DEFAULT 0,
    lastSynchronizedHash,
    lastSynchronizedTimestamp NOT NULL DEFAULT -63113817600,
    metadataPresetID,
    metadataVersion,
    monochrome INTEGER NOT NULL DEFAULT 0,
    xmp NOT NULL DEFAULT ''
);
CREATE TABLE Adobe_imageDevelopSettings (
    id_local INTEGER PRIMARY KEY,
    allowFastRender INTEGER,
    beforeSettingsIDCache,
    croppedHeight,
    croppedWidth,
    digest,
    fileHeight,
    fileWidth,
    grayscale INTEGER,
    hasAIMasks INTEGER NOT NULL DEFAULT 0,
    hasBigData INTEGER NOT NULL DEFAULT 0,
    hasDevelopAdjustments INTEGER,
    hasDevelopAdjustmentsEx,
    hasLensBlur INTEGER NOT NULL DEFAULT 0,
    hasMasks INTEGER NOT NULL DEFAULT 0,
    hasPointColor INTEGER NOT NULL DEFAULT 0,
    hasRetouch,
    hasSettings1,
    hasSettings2,
    historySettingsID,
    image INTEGER,
    isHdrEditMode INTEGER NOT NULL DEFAULT 0,
    processVersion,
    profileCorrections,
    removeChromaticAberration,
    settingsID,
    snapshotID,
    text,
    validatedForVersion,
    whiteBalance
);
CREATE TABLE Adobe_images (
    id_local INTEGER PRIMARY KEY,
    id_global UNIQUE NOT NULL,
    aspectRatioCache NOT NULL DEFAULT -1,
    bitDepth NOT NULL DEFAULT 0,
    captureTime,
    colorChannels NOT NULL DEFAULT 0,
    colorLabels NOT NULL DEFAULT '',
    colorMode NOT NULL DEFAULT -1,
    copyCreationTime NOT NULL DEFAULT -63113817600,
    copyName,
    copyReason,
    developSettingsIDCache,
    editLock INTEGER NOT NULL DEFAULT 0,
    fileFormat NOT NULL DEFAULT 'unset',
    fileHeight,
    fileWidth,
    hasMissingSidecars INTEGER,
    masterImage INTEGER,
    orientation,
    originalCaptureTime,
    originalRootEntity INTEGER,
    panningDistanceH,
    panningDistanceV,
    pick NOT NULL DEFAULT 0,
    positionInFolder NOT NULL DEFAULT 'z',
    propertiesCache,
    pyramidIDCache,
    rating,
    rootFile INTEGER NOT NULL DEFAULT 0,
    sidecarStatus,
    touchCount NOT NULL DEFAULT 0,
    touchTime NOT NULL DEFAULT 0
);
CREATE TABLE Adobe_libraryImageDevelopHistoryStep (
    id_local INTEGER PRIMARY KEY,
    id_global UNIQUE NOT NULL,
    dateCreated,
    digest,
    hasBigData INTEGER NOT NULL DEFAULT 0,
    hasDevelopAdjustments,
    image INTEGER,
    name,
    relValueString,
    text,
    valueString
);
CREATE TABLE Adobe_variablesTable (
	    id_local INTEGER PRIMARY KEY,
	    id_global UNIQUE NOT NULL,
	    name,
	    type,
	    value NOT NULL DEFAULT ''
	);
CREATE TABLE AgHarvestedExifMetadata (
    id_local INTEGER PRIMARY KEY,
    image INTEGER,
    aperture,
    cameraModelRef INTEGER,
    cameraSNRef INTEGER,
    dateDay,
    dateMonth,
    dateYear,
    flashFired INTEGER,
    focalLength,
    gpsLatitude,
    gpsLongitude,
    gpsSequence NOT NULL DEFAULT 0,
    hasGPS INTEGER,
    isoSpeedRating,
    lensRef INTEGER,
    shutterSpeed
);
CREATE TABLE AgHarvestedIptcMetadata (
    id_local INTEGER PRIMARY KEY,
    image INTEGER,
    cityRef INTEGER,
    copyrightState INTEGER,
    countryRef INTEGER,
    creatorRef INTEGER,
    isoCountryCodeRef INTEGER,
    jobIdentifierRef INTEGER,
    locationDataOrigination NOT NULL DEFAULT 'unset',
    locationGPSSequence NOT NULL DEFAULT -1,
    locationRef INTEGER,
    stateRef INTEGER
);
CREATE TABLE AgInternedExifCameraModel (
    id_local INTEGER PRIMARY KEY,
    searchIndex,
    value
);
CREATE TABLE AgInternedExifCameraSN (
    id_local INTEGER PRIMARY KEY,
    searchIndex,
    value
);
CREATE TABLE AgInternedExifLens (
    id_local INTEGER PRIMARY KEY,
    searchIndex,
    value
);
CREATE TABLE AgInternedIptcCity (
    id_local INTEGER PRIMARY KEY,
    searchIndex,
    value
);
CREATE TABLE AgInternedIptcCountry (
    id_local INTEGER PRIMARY KEY,
    searchIndex,
    value
);
CREATE TABLE AgInternedIptcCreator (
    id_local INTEGER PRIMARY KEY,
    searchIndex,
    value
);
CREATE TABLE AgInternedIptcLocation (
    id_local INTEGER PRIMARY KEY,
    searchIndex,
    value
);
CREATE TABLE AgInternedIptcState (
    id_local INTEGER PRIMARY KEY,
    searchIndex,
    value
);
CREATE TABLE AgLibraryCollection (
    id_local INTEGER PRIMARY KEY,
    creationId NOT NULL DEFAULT '',
    genealogy NOT NULL DEFAULT '',
    imageCount,
    name NOT NULL DEFAULT '',
    parent INTEGER,
    systemOnly NOT NULL DEFAULT ''
);
CREATE TABLE AgLibraryCollectionContent (
    id_local INTEGER PRIMARY KEY,
    collection INTEGER NOT NULL DEFAULT 0,
    content,
    owningModule
);
CREATE TABLE AgLibraryCollectionImage (
    id_local INTEGER PRIMARY KEY,
    collection INTEGER NOT NULL DEFAULT 0,
    image INTEGER NOT NULL DEFAULT 0,
    pick NOT NULL DEFAULT 0,
    positionInCollection
);
CREATE TABLE AgLibraryFile (
    id_local INTEGER PRIMARY KEY,
    id_global UNIQUE NOT NULL,
    baseName NOT NULL DEFAULT '',
    errorMessage,
    errorTime,
    extension NOT NULL DEFAULT '',
    externalModTime,
    folder INTEGER NOT NULL DEFAULT 0,
    idx_filename NOT NULL DEFAULT '',
    importHash,
    lc_idx_filename NOT NULL DEFAULT '',
    lc_idx_filenameExtension NOT NULL DEFAULT '',
    md5,
    modTime,
    originalFilename NOT NULL DEFAULT '',
    sidecarExtensions
);
CREATE TABLE AgLibraryFolder (
    id_local INTEGER PRIMARY KEY,
    id_global UNIQUE NOT NULL,
    parentId INTEGER,
    pathFromRoot NOT NULL DEFAULT '',
    rootFolder INTEGER NOT NULL DEFAULT 0,
    visibility INTEGER
);
CREATE TABLE AgLibraryFolderStackImage (
    id_local INTEGER PRIMARY KEY,
    collapsed INTEGER NOT NULL DEFAULT 0,
    image INTEGER NOT NULL DEFAULT 0,
    position NOT NULL DEFAULT '',
    stack INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE AgLibraryIPTC (
    id_local INTEGER PRIMARY KEY,
    altTextAccessibility,
    caption,
    copyright,
    extDescrAccessibility,
    image INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE AgLibraryImport (
    id_local INTEGER PRIMARY KEY,
    imageCount,
    importDate NOT NULL DEFAULT '',
    name
);
CREATE TABLE AgLibraryImportImage (
    id_local INTEGER PRIMARY KEY,
    image INTEGER NOT NULL DEFAULT 0,
    import INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE AgLibraryKeyword (
    id_local INTEGER PRIMARY KEY,
    id_global UNIQUE NOT NULL,
    dateCreated NOT NULL DEFAULT '',
    genealogy NOT NULL DEFAULT '',
    imageCountCache DEFAULT -1,
    includeOnExport INTEGER NOT NULL DEFAULT 1,
    includeParents INTEGER NOT NULL DEFAULT 1,
    includeSynonyms INTEGER NOT NULL DEFAULT 1,
    keywordType,
    lastApplied,
    lc_name,
    name,
    parent INTEGER
);
CREATE TABLE AgLibraryKeywordImage (
    id_local INTEGER PRIMARY KEY,
    image INTEGER NOT NULL DEFAULT 0,
    tag INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE AgLibraryPublishedCollection (
    id_local INTEGER PRIMARY KEY,
    creationId NOT NULL DEFAULT '',
    genealogy NOT NULL DEFAULT '',
    imageCount,
    isDefaultCollection,
    name NOT NULL DEFAULT '',
    parent INTEGER,
    publishedUrl,
    remoteCollectionId,
    systemOnly NOT NULL DEFAULT ''
);
CREATE TABLE AgLibraryPublishedCollectionImage (
    id_local INTEGER PRIMARY KEY,
    collection INTEGER NOT NULL DEFAULT 0,
    image INTEGER NOT NULL DEFAULT 0,
    pick NOT NULL DEFAULT 0,
    positionInCollection
);
CREATE TABLE AgLibraryRootFolder (
    id_local INTEGER PRIMARY KEY,
    id_global UNIQUE NOT NULL,
    absolutePath UNIQUE NOT NULL DEFAULT '',
    name NOT NULL DEFAULT '',
    relativePathFromCatalog
);
CREATE TABLE AgMetadataSearchIndex (
    id_local INTEGER PRIMARY KEY,
    exifSearchIndex NOT NULL DEFAULT '',
    image INTEGER,
    iptcSearchIndex NOT NULL DEFAULT '',
    otherSearchIndex NOT NULL DEFAULT '',
    searchIndex NOT NULL DEFAULT ''
);
CREATE TABLE AgRemotePhoto (
    id_local INTEGER PRIMARY KEY,
    id_global UNIQUE NOT NULL,
    collection INTEGER NOT NULL DEFAULT 0,
    commentCount,
    developSettingsDigest,
    fileContentsHash,
    fileModTimestamp,
    metadataDigest,
    mostRecentCommentTime,
    orientation,
    photo INTEGER NOT NULL DEFAULT 0,
    photoNeedsUpdating DEFAULT 2,
    publishCount,
    remoteId,
    serviceAggregateRating,
    url
);
CREATE TABLE AgSourceColorProfileConstants (
    id_local INTEGER PRIMARY KEY,
    image INTEGER NOT NULL DEFAULT 0,
    profileName NOT NULL DEFAULT 'Untagged'
);
CREATE TABLE AgVideoInfo (
    id_local INTEGER PRIMARY KEY,
    duration,
    frame_rate,
    has_audio INTEGER NOT NULL DEFAULT 1,
    has_video INTEGER NOT NULL DEFAULT 1,
    image INTEGER NOT NULL DEFAULT 0,
    poster_frame NOT NULL DEFAULT '0000000000000000/0000000000000001',
    poster_frame_set_by_user INTEGER NOT NULL DEFAULT 0,
    trim_end NOT NULL DEFAULT '0000000000000000/0000000000000001',
    trim_start NOT NULL DEFAULT '0000000000000000/0000000000000001'
);
