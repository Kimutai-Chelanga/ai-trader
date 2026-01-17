# Makefile for AI-Trader with Alembic

.PHONY: help setup db-shell db-backup db-restore

help: ## Show this help message
	@echo "AI-Trader Alembic Migration Commands"
	@echo "====================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# ============================================================
# Setup Commands
# ============================================================

setup: ## Initial setup - creates alembic structure
	python alembic_setup.py
	@echo ""
	@echo "Next steps:"
	@echo "1. Review models.py and alembic.ini"
	@echo "2. Create initial migration: make alembic-revision MESSAGE='initial schema'"
	@echo "3. Apply migrations: make alembic-upgrade"

# ============================================================
# Alembic Migration Commands
# ============================================================

alembic-current: ## Show current migration revision
	docker-compose run --rm alembic alembic current

alembic-history: ## Show migration history
	docker-compose run --rm alembic alembic history --verbose

alembic-upgrade: ## Apply all pending migrations (upgrade to head)
	docker-compose run --rm alembic alembic upgrade head

alembic-upgrade-one: ## Upgrade by one migration
	docker-compose run --rm alembic alembic upgrade +1

alembic-downgrade: ## Downgrade by one migration
	docker-compose run --rm alembic alembic downgrade -1

alembic-downgrade-base: ## Downgrade to base (WARNING: removes all migrations)
	docker-compose run --rm alembic alembic downgrade base

alembic-revision: ## Create a new migration (usage: make alembic-revision MESSAGE="add column")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required"; \
		echo "Usage: make alembic-revision MESSAGE='your migration message'"; \
		exit 1; \
	fi
	docker-compose run --rm alembic alembic revision --autogenerate -m "$(MESSAGE)"

alembic-revision-manual: ## Create empty migration file for manual editing
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required"; \
		exit 1; \
	fi
	docker-compose run --rm alembic alembic revision -m "$(MESSAGE)"

alembic-show: ## Show SQL for a specific revision (usage: make alembic-show REV=head)
	docker-compose run --rm alembic alembic show $(REV)

alembic-stamp: ## Mark database as being at a specific revision without running migrations
	@if [ -z "$(REV)" ]; then \
		echo "Error: REV is required"; \
		echo "Usage: make alembic-stamp REV=head"; \
		exit 1; \
	fi
	docker-compose run --rm alembic alembic stamp $(REV)

# ============================================================
# Database Commands
# ============================================================

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U aitrader -d trading_db

db-connect: ## Same as db-shell
	docker-compose exec postgres psql -U aitrader -d trading_db

db-backup: ## Backup database to file
	@mkdir -p backups
	docker-compose exec -T postgres pg_dump -U aitrader trading_db > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created in backups/"

db-restore: ## Restore from latest backup
	@LATEST=$$(ls -t backups/*.sql | head -1); \
	if [ -z "$$LATEST" ]; then \
		echo "❌ No backup files found"; \
		exit 1; \
	fi; \
	echo "Restoring from $$LATEST"; \
	docker-compose exec -T postgres psql -U aitrader trading_db < $$LATEST

db-logs: ## Show PostgreSQL logs
	docker-compose logs -f postgres

db-reset: ## Reset database (WARNING: destructive!)
	@echo "⚠️  This will delete ALL data!"
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose down -v; \
		docker-compose up -d postgres; \
		sleep 5; \
		make alembic-upgrade; \
	else \
		echo "Cancelled"; \
	fi

# ============================================================
# Docker Commands
# ============================================================

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

rebuild: ## Rebuild all services
	docker-compose build
	docker-compose up -d

logs: ## Show logs for all services
	docker-compose logs -f

clean: ## Remove all containers and volumes
	docker-compose down -v
	rm -rf postgres_data

# ============================================================
# Development Workflow
# ============================================================

dev-init: ## Initialize development environment
	@echo "🚀 Initializing AI-Trader development environment"
	cp .env.example .env || true
	mkdir -p backups data alembic/versions
	docker-compose build
	docker-compose up -d postgres
	@echo "⏳ Waiting for PostgreSQL..."
	sleep 10
	make alembic-upgrade
	@echo "✅ Development environment ready!"

dev-new-migration: ## Quick workflow: create and apply migration
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required"; \
		exit 1; \
	fi
	make alembic-revision MESSAGE="$(MESSAGE)"
	@echo ""
	@echo "📝 Review the migration file in alembic/versions/"
	@read -p "Apply this migration? (y/n): " apply; \
	if [ "$$apply" = "y" ]; then \
		make alembic-upgrade; \
	fi

dev-status: ## Show development environment status
	@echo "Database Status:"
	@echo "================"
	docker-compose ps
	@echo ""
	@echo "Current Migration:"
	@echo "=================="
	make alembic-current
	@echo ""
	@echo "Pending Migrations:"
	@echo "==================="
	@docker-compose run --rm alembic alembic history | head -10

# ============================================================
# Testing
# ============================================================

test-migration: ## Test a migration up and down
	@echo "Testing migration..."
	make alembic-upgrade
	@echo "✅ Upgrade successful"
	@read -p "Press Enter to test downgrade..."
	make alembic-downgrade
	@echo "✅ Downgrade successful"
	@read -p "Press Enter to re-apply..."
	make alembic-upgrade
	@echo "✅ Migration test complete"

# ============================================================
# Production Helpers
# ============================================================

prod-check: ## Pre-deployment checks
	@echo "Running pre-deployment checks..."
	@echo ""
	@echo "1. Database backup..."
	make db-backup
	@echo ""
	@echo "2. Checking pending migrations..."
	docker-compose run --rm alembic alembic current
	@echo ""
	@echo "3. Showing SQL that will be executed..."
	docker-compose run --rm alembic alembic upgrade head --sql
	@echo ""
	@echo "✅ Checks complete. Review SQL above before deploying."

prod-deploy: ## Deploy migrations to production (after review)
	@echo "⚠️  Deploying to production"
	@read -p "Have you reviewed the SQL? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		make alembic-upgrade; \
		echo "✅ Deployment complete"; \
	else \
		echo "❌ Deployment cancelled"; \
	fi