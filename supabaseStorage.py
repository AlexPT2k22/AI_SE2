import uuid
from typing import Optional, Any
from supabase import create_client, Client


class SupabaseStorageService:
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        bucket_name: str = "parking-images",
        public_bucket: bool = False,
    ):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.bucket = bucket_name
        self.public_bucket = public_bucket
        self.base_public_url = f"{supabase_url}/storage/v1/object/public/{self.bucket}"

    # -------------------------
    # Gera caminho do ficheiro
    # -------------------------
    def _generate_file_path(self, plate: str, ext: str = "jpg") -> str:
        return f"{plate}/{uuid.uuid4()}.{ext}"

    # -------------------------
    # Upload da imagem
    # -------------------------
    def upload_image(self, image_bytes: bytes, plate: str, ext: str = "jpg") -> str:
        file_path = self._generate_file_path(plate, ext)

        res = self.supabase.storage.from_(self.bucket).upload(
            path=file_path,
            file=image_bytes,
            file_options={"content-type": f"image/{ext}"},
        )

        # Nova lib → objeto UploadResponse / StorageResponse
        # Tenta lidar tanto com objeto como com dict (para compatibilidade)
        error = None

        if hasattr(res, "error"):
            error = res.error
        elif isinstance(res, dict) and "error" in res:
            error = res["error"]

        if error:
            raise Exception(f"[Supabase Upload Error] {error}")

        return file_path

    # -------------------------
    # URL pública (bucket público)
    # -------------------------
    def get_public_url(self, file_path: str) -> str:
        if not self.public_bucket:
            raise Exception("Bucket is not public. Use get_signed_url() instead.")

        return f"{self.base_public_url}/{file_path}"

    # -------------------------
    # Signed URL (bucket privado)
    # -------------------------
    def get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        res = self.supabase.storage.from_(self.bucket).create_signed_url(
            file_path, expires_in
        )

        error = None
        data: Any = None

        if hasattr(res, "error"):
            error = res.error
            data = getattr(res, "data", None)
        elif isinstance(res, dict):
            error = res.get("error")
            data = res.get("data")
            if data is None:
                # Algumas versões retornam diretamente os campos signedURL/signedUrl
                data = res

        if error:
            raise Exception(f"[Supabase Signed URL Error] {error}")

        signed_url = None
        if isinstance(data, dict):
            signed_url = data.get("signedURL") or data.get("signedUrl")
        elif isinstance(data, str):
            signed_url = data

        if signed_url:
            return signed_url

        raise Exception(f"[Supabase Signed URL Error] Unexpected response: {res}")

    # -------------------------
    # Upload + URL final
    # -------------------------
    def upload_and_get_url(
        self,
        image_bytes: bytes,
        plate: str,
        expires_in: int = 3600,
        ext: str = "jpg",
    ) -> str:
        file_path = self.upload_image(image_bytes=image_bytes, plate=plate, ext=ext)

        if self.public_bucket:
            return self.get_public_url(file_path)

        return self.get_signed_url(file_path, expires_in)
