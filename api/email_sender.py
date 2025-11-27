from mailjet_rest import Client
import os

MAILJET_API_KEY = "481fdef143b2c95563524b5b64872a5d"
MAILJET_SECRET_KEY = "08320c0246573410fc0f65f3f5c1927e"

mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')

def enviar_email_recomendaciones(destinatario: str, recomendaciones: list):
    print("Enviando email a:", destinatario)

    # Diseño minimalista para cada recomendación
    lista_html = "".join(
        [
            f"""
            <div style="
                padding: 12px 16px; 
                border: 1px solid #e5e5e5; 
                border-radius: 8px; 
                margin-bottom: 12px;
                font-family: Arial, sans-serif;
            ">
                <div style="font-size: 16px; font-weight: bold; color: #222;">
                    🎬 {rec['titulo']}
                </div>
                <div style="font-size: 13px; color: #555; margin-top: 2px;">
                    IMDb: {rec['imdb_id']}
                </div>

                <div style="
                    margin-top: 8px; 
                    padding-top: 8px; 
                    border-top: 1px solid #eee; 
                    font-size: 13px; 
                    color: #444;
                ">
                    <strong>Detalles técnicos</strong><br>
                    Valoración Esperada: {rec['prediccion_svd']}<br>
                    Similitud con favoritos: {rec['similitud_con_favoritos']}<br>
                    Afinidad por género: {rec['afinidad_genero']}<br>
                </div>
            </div>
            """
            for rec in recomendaciones
        ]
    )

    data = {
        'Messages': [
            {
                "From": {
                    "Email": "juantabordaacosta@gmail.com",
                    "Name": "MovieRecommender"
                },
                "To": [
                    {
                        "Email": destinatario,
                        "Name": "Usuario"
                    }
                ],
                "Subject": "Tus recomendaciones de películas 🎬",
                "HTMLPart": f"""
                    <div style="font-family: Arial, sans-serif; color: #222;">
                        <h2 style="font-weight: bold;">Tus películas recomendadas</h2>

                        <p style="font-size: 14px; color: #444;">
                            Aquí tienes una selección basada en tu perfil, favoritos y afinidades.
                        </p>

                        {lista_html}

                        <p style="margin-top: 25px; font-size: 13px; color: #777;">
                            Gracias por usar nuestro recomendador 🎬<br>
                            — Equipo JD TEAM
                        </p>
                    </div>
                """
            }
        ]
    }

    result = mailjet.send.create(data=data)
    print("Email enviado, status:", result.status_code)
    return result.status_code, result.json()