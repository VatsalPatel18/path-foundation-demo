from ez_wsi_dicomweb import credential_factory
from ez_wsi_dicomweb import dicom_slide
from ez_wsi_dicomweb import dicom_web_interface
from ez_wsi_dicomweb import patch_embedding
from ez_wsi_dicomweb import patch_embedding_endpoints
from ez_wsi_dicomweb.ml_toolkit import dicom_path


if __name__ == '__main__':
  endpoint = patch_embedding_endpoints.V2PatchEmbeddingEndpoint(credential_factory=credential_factory.NoAuthCredentialsFactory())
  endpoint._end_point_url = 'http://127.0.0.1/predict'

  dwi = dicom_web_interface.DicomWebInterface(credential_factory.NoAuthCredentialsFactory())
  path = dicom_path.FromString("https://proxy.imaging.datacommons.cancer.gov/current/viewer-only-no-downloads-see-tinyurl-dot-com-slash-3j3d9jyp/dicomWeb/studies/2.25.247578737460869511622147617375340640521/series/1.3.6.1.4.1.5962.99.1.1334257398.450227235.1637716829942.2.0")
  slide = dicom_slide.DicomSlide(dwi, path)
  patch = slide.get_patch(slide.native_level, 0,0, 224,224)
  embedding = patch_embedding.get_patch_embedding(endpoint, patch)
  print(embedding)
