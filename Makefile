test:
	docker compose exec web coverage run manage.py test backend users && \
	docker compose exec web coverage report -m
up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f web

clean:
	docker compose down -v
	docker system prune -f

superuser:
	docker compose exec web python manage.py createsuperuser

restart:
	docker compose restart web