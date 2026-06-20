from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from users.models import User as UserProfile
from transactions.models import Transacao, Category
from decimal import Decimal

User = get_user_model()

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Obter a categoria padrão (já semeada via migrações)
        self.category = Category.objects.get(name="Alimentação")
        
        # Criar perfil pré-existente no banco de dados para simular "conversa no whatsapp"
        self.phone_valid = "5511999998888"
        self.profile_unlinked = UserProfile.objects.create(
            name="Test User Unlinked",
            phone_number=self.phone_valid,
            time_zone="America/Sao_Paulo",
            locale="pt_BR"
        )
        
        # Criar usuário cadastrado para testes de login e isolamento
        self.user_registered = User.objects.create_user(
            username="registered@example.com",
            email="registered@example.com",
            password="securepassword123",
            first_name="Registered User"
        )
        self.phone_registered = "5511977776666"
        self.profile_linked = UserProfile.objects.create(
            auth_user=self.user_registered,
            name="Registered User",
            phone_number=self.phone_registered,
            time_zone="America/Sao_Paulo",
            locale="pt_BR"
        )
        
        # Criar transações para o usuário registrado
        self.t1 = Transacao.objects.create(
            user=self.user_registered,
            category=self.category,
            description="Mercado",
            value=Decimal("150.50"),
            type="OUT"
        )
        
        # Criar outro usuário com suas próprias transações para testar isolamento
        self.other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="otherpassword123",
            first_name="Other User"
        )
        self.other_phone = "5511911112222"
        self.other_profile = UserProfile.objects.create(
            auth_user=self.other_user,
            name="Other User",
            phone_number=self.other_phone
        )
        self.t_other = Transacao.objects.create(
            user=self.other_user,
            category=self.category,
            description="Lazer",
            value=Decimal("80.00"),
            type="OUT"
        )

    def test_dashboard_requires_login(self):
        """Acesso direto ao dashboard sem login deve redirecionar para a tela de login."""
        response = self.client.get(reverse('dashboard_index'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard_index')}")

    def test_login_page_renders_successfully(self):
        """Página de login deve renderizar para usuários anônimos."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/login.html')

    def test_cadastro_page_renders_successfully(self):
        """Página de cadastro deve renderizar para usuários anônimos."""
        response = self.client.get(reverse('cadastro'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/cadastro.html')

    def test_login_success(self):
        """Login com e-mail e senha corretos deve redirecionar para o dashboard."""
        response = self.client.post(reverse('login'), {
            'email': 'registered@example.com',
            'password': 'securepassword123'
        })
        self.assertRedirects(response, reverse('dashboard_index'))

    def test_login_failure(self):
        """Login com credenciais inválidas deve exibir erro na tela."""
        response = self.client.post(reverse('login'), {
            'email': 'registered@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], None, "E-mail ou senha incorretos.")

    def test_cadastro_failure_phone_not_exists(self):
        """Cadastro com telefone inexistente na base de conversas deve falhar com a mensagem exigida."""
        response = self.client.post(reverse('cadastro'), {
            'nome': 'Novo Usuário',
            'email': 'newuser@example.com',
            'phone_number': '5511999990000', # número inexistente
            'password': 'newpassword123',
            'password_confirm': 'newpassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 
            'phone_number', 
            "Não é possível finalizar o cadastro, pois o número de telefone não está vinculado "
            "a nenhuma conversa com o assistente no WhatsApp."
        )

    def test_cadastro_failure_phone_already_linked(self):
        """Cadastro com telefone que já possui conta de login associada deve falhar."""
        response = self.client.post(reverse('cadastro'), {
            'nome': 'Outro Nome',
            'email': 'duplicate@example.com',
            'phone_number': self.phone_registered, # já está vinculado a self.user_registered
            'password': 'newpassword123',
            'password_confirm': 'newpassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 
            'phone_number', 
            "Este número de telefone já está associado a uma conta cadastrada."
        )

    def test_cadastro_success_with_normalization(self):
        """Cadastro bem-sucedido com telefone formatado. O telefone deve ser normalizado, o usuário criado e vinculado."""
        # Enviar telefone formatado
        formatted_phone = "+55 (11) 99999-8888" # normaliza para self.phone_valid
        response = self.client.post(reverse('cadastro'), {
            'nome': 'Usuário Cadastrado',
            'email': 'success@example.com',
            'phone_number': formatted_phone,
            'password': 'newpassword123',
            'password_confirm': 'newpassword123'
        })
        self.assertRedirects(response, reverse('dashboard_index'))
        
        # Verificar criação do usuário
        user_exists = User.objects.filter(email='success@example.com').exists()
        self.assertTrue(user_exists)
        
        # Verificar vinculação e normalização
        new_user = User.objects.get(email='success@example.com')
        profile = UserProfile.objects.get(phone_number=self.phone_valid)
        self.assertEqual(profile.auth_user, new_user)
        self.assertEqual(profile.name, 'Usuário Cadastrado')

    def test_dashboard_data_isolation(self):
        """Garantir que os dados exibidos no dashboard/API são estritamente do usuário logado."""
        # Logar o usuário registrado
        self.client.login(username='registered@example.com', password='securepassword123')
        
        # Consultar resumo
        response = self.client.get(reverse('resumo_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # O usuário registrado deve ver apenas suas despesas (t1 = 150.50)
        self.assertEqual(data['total_despesas'], 150.50)
        
        # Transações retornadas devem listar apenas a sua transação
        transacoes_retornadas = data['transacoes']
        self.assertEqual(len(transacoes_retornadas), 1)
        self.assertEqual(transacoes_retornadas[0]['descricao'], "Mercado")
        
        # Nenhuma informação de t_other (Other User) deve estar listada
        for t in transacoes_retornadas:
            self.assertNotEqual(t['descricao'], "Lazer")
